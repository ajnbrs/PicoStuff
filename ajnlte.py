from machine import UART, Pin
from network import PPP
from micropython import const
from machine import Pin, PWM
import time
from ajnpdu import SMS_DELIVER

DEFAULT_PIN_RST = 11
DEFAULT_PIN_NETLIGHT = 10
DEFAULT_PIN_RX = 9
DEFAULT_PIN_TX = 8
DEFAULT_UART_ID = 1

# DEFAULT_PIN_RST = 35
# DEFAULT_PIN_NETLIGHT = 34
# DEFAULT_PIN_RX = 33
# DEFAULT_PIN_TX = 32
# DEFAULT_UART_ID = 0

DEFAULT_UART_TIMEOUT = const(1)
DEFAULT_UART_TIMEOUT_CHAR = const(1)
DEFAULT_UART_RXBUF = const(1024)
DEFAULT_UART_STARTUP_BAUD = const(460800)
DEFAULT_UART_BAUD = const(460800)
        
class CellularError(Exception):
  def __init__(self, message=None):
    self.message = "CellularError: " + message
        
class LTE():
    def __init__(self, apn, uart=None, reset_pin=None, verbose=True):
        self._apn = apn
        self._reset = reset_pin or Pin(DEFAULT_PIN_RST, Pin.OUT)
        self._uart = uart or UART(
            DEFAULT_UART_ID,
            tx=Pin(DEFAULT_PIN_TX, Pin.OUT),
            rx=Pin(DEFAULT_PIN_RX, Pin.OUT))
        # Set PPP timeouts and rxbuf
        self._uart.init(
            timeout=DEFAULT_UART_TIMEOUT,
            timeout_char=DEFAULT_UART_TIMEOUT_CHAR,
            rxbuf=DEFAULT_UART_RXBUF)
        
        self._verbose = verbose
        
        self._reset.value(0)
        time.sleep(1.0)
        self._reset.value(1)
        
        self._ppp = PPP(self._uart)
        
        self.operator = None

    def delete_message(self, msg_num):
        ppp_state = self._ppp.isconnected()
        if ppp_state:
            self.internet_off()
        try:
            self._wait_ready()
            self._send_at_command(f"AT+CMGL={msg_num}")
        except CellularError:
           pass
        finally:
            if ppp_state:
                self.internet_on()
    
    def send_message(self, recipient, body, timeout=5.0):
        ppp_state = self._ppp.isconnected()
        if ppp_state:
            self.internet_off()
        try:
            self._wait_ready()
            self._send_at_command("AT+CMGF=1")
            self._send_at_command(f"AT+CMGS=\"{recipient}\"")
            time.sleep(0.5)
            self._send_at_command(f"{body}\x1a")
        except CellularError:
           pass    
        finally:
            if ppp_state:
                self.internet_on()
    
    def get_messages(self, sender=None):
        ppp_state = self._ppp.isconnected()
        if ppp_state:
            self.internet_off()
        try:
            self._wait_ready()
            self._send_at_command(f"AT+CMGF=0")
            data = self._send_at_command(f"AT+CMGL=4")
            messages = []
            for i in range(0, len(data), 2):
                msg_num = int(data[i][6:].split(b',')[0])
                pdu = SMS_DELIVER(data[i+1].decode())
                if sender is not None and sender != pdu.sender_number:
                    continue
                msg_id=''
                if pdu.tp_udhi:
                    msg_id = pdu.tp_udh[:-2]
                else:
                    msg_id = f'{pdu.sender_number}-{msg_num}'
                messages.append([msg_num, msg_id, pdu.part, pdu.sender_number, pdu.message, pdu.timestamp])
            combined = self._combine_messages(messages)
            return sorted(combined, key=lambda d: d['timestamp'], reverse=True)
        except CellularError:
           pass
        finally:
            if ppp_state:
                self.internet_on()
    
    def get_status(self):
        ppp_state = self._ppp.isconnected()
        if ppp_state:
            self.internet_off()
        try:
            self._wait_ready()
            lte_status = self._send_at_command("AT+CEREG?", 1).decode()
            gsm_status = self._send_at_command("AT+CGREG?", 1).decode()
            return int(lte_status[-1]), int(gsm_status[-1])
        except CellularError:
           pass
        finally:
            if ppp_state:
                self.internet_on()
    
    def get_iccid(self):
        ppp_state = self._ppp.isconnected()
        if ppp_state:
            self.internet_off()
        try:
            self._wait_ready()
            return self._send_at_command("AT+CICCID", 1)[8:].decode()
        except CellularError:
           pass
        finally:
            if ppp_state:
                self.internet_on()
                
    def get_signal(self):
        ppp_state = self._ppp.isconnected()
        if ppp_state:
            self.internet_off()
        try:
            self._wait_ready()
            response = self._send_at_command("AT+CSQ", 1)
            quality = int(response.split(b":")[1].split(b",")[0])
            db = -113 + (2 * quality) # conversion as per AT command set datasheet
            return db
        except CellularError:
            pass
        finally:
            if ppp_state:
                self.internet_on()
    
    def get_datetime(self):
        ppp_state = self._ppp.isconnected()
        if ppp_state:
            self.internet_off()
        try:
            self._wait_ready()
            data = self._send_at_command("AT+CCLK?", 1)
            cclk = data.decode()[8:-1]
            d, t = cclk.split(",")
            d = '/'.join(reversed(d.split('/')))
            return f'{d} {t}'
        except CellularError:
            pass
        finally:
            if ppp_state:
                self.internet_on()
                
    def internet_on(self):
        self._uart.write("ATD*99#\r")
        self._uart.flush()
        time.sleep(0.5)
        self._ppp.connect()
        
    def internet_off(self):
        self._ppp.disconnect()
    
    def reset(self):
        con._reset.value(0)
        time.sleep(1.0)
        con._reset.value(1)
    
    def connect(self, timeout=60):
        
        print("  - setting up cellular uart")
        # connect to and flush the uart
        # consume any unsolicited messages first, we don't need those  
        self._flush_uart()

        print("  - waiting for cellular module to be ready")

        # wait for the cellular module to respond to AT commands
        self._wait_ready()   

        self._send_at_command("ATE0") # disable local echo  
        self._send_at_command(f"AT+CGDCONT=1,\"IP\",\"{self._apn}\"") # set apn and activate pdp context  

        # wait for roaming lte connection to be established
        giveup = time.time() + timeout
        status = None
        while status != b"+CEREG: 0,5" and status != b"+CEREG: 0,1":
            status = self._send_at_command("AT+CEREG?", 1)
            time.sleep(0.25)
            if time.time() > giveup:
                raise CellularError("timed out getting network registration")    

        # disable server and client certification validation
        self._send_at_command("AT+CSSLCFG=\"authmode\",0,0") 
        self._send_at_command("AT+CSSLCFG=\"enableSNI\",0,1")

        self._send_at_command("AT+CTZU=1") # time/timezone autoupdate
        
        op = self._send_at_command("AT+CSPN?", 1).decode()
        self.operator = op[8:op.find('"',8)] # set operator name
    
    def _combine_messages(self, data):
        msg_dict={}
        for msg in data:
            if msg_dict.get(msg[1], '') == '':
                msg_dict[msg[1]] = { 'sender':msg[3], 'timestamp': msg[5], 'parts': { msg[2]: [msg[0], msg[4]] } }
            else:
                msg_dict[msg[1]]['parts'][msg[2]] = [msg[0], msg[4]]
        messages = list(msg_dict.values())
        for msg in messages:
            out = ''
            parts = dict(sorted(msg['parts'].items()))
            for i in range(1, len(parts)+1):
                out += parts[i][1]
            msg['formatted_message'] = out
        return messages

    def _wait_ready(self, poll_time=0.25, timeout=10):
        giveup = time.time() + timeout
        while time.time() <= giveup:
            try:
                self._send_at_command("AT")
                return # if __send_at_command doesn't throw an exception then we're good!
            except CellularError as e:
                print(e)
                time.sleep(poll_time)
        raise CellularError("timed out waiting for AT response")  

    def _flush_uart(self):
        self._uart.flush()
        time.sleep(0.25)
        while self._uart.any():
            self._uart.read(self._uart.any())
            time.sleep(0.25)

    def _send_at_command(self, command, result_lines=0, timeout=5.0):
        # consume any unsolicited messages first, we don't need those    
        self._flush_uart()

        self._uart.write(command + "\r")
        #print(f"  - tx: {command}")
        self._uart.flush()
        status, data = self._read_result(result_lines, timeout=timeout)

        if self._verbose:
            print("  -", command, status, data)

        if status == "TIMEOUT":
            #print.error("  !", command, status, data)
            raise CellularError(f"cellular module timed out for command {command}")

        if status not in [">", "OK", "DOWNLOAD"]:
            #print("  !", command, status, data)
            raise CellularError(f"non 'OK' or 'DOWNLOAD' result for command {command}")

        if result_lines == 1:
            return data[0]
        return data

    def _read_result(self, result_lines, timeout=1.0):
        status = None
        result = []
        start = time.ticks_ms()
        timeout *= 1000
        while len(result) < result_lines or status is None:
            if (time.ticks_ms() - start) > timeout:
                return "TIMEOUT", []

            line = self._uart.readline()

            if line:
                #print(line)
                line = line.strip()
                if line in [b">", b"OK", b"ERROR", b"DOWNLOAD"]:
                    status = line.decode("ascii")
                elif line != b"":
                    result.append(line)
                start = time.ticks_ms()

        return status, result