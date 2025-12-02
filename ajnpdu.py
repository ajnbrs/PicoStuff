pdu0='0791444740003017040C9144979490479700F15211820250550005D4F29C0E02'
pdu12='07914447400030964414D0CCFC380C6ABEC56976190008521192209091003A050003C003030065002000630065006E0074007200650020007400650061006D00200069006D006D006500640069006100740065006C0079002E'
pdu1='07914447400010714412D0CCFC38DC7C8BD3EC32000052119271405240610500031102024081180CF49683DA6F793904A2BE41EA77DACD02C9CB70761E744FD3D1A0580D14769341F6F43C4DD781EEF7BB8B991F879B6F719A5D768DDFAEFAFAC57EE7C36C7A1EE4A296E5ED39280C87B3F32E'
pdu2='07914447400010714412D0CCFC38DC7C8BD3EC32000052119271405240A0050003110201B2EFFA495E06A5DDF634BD4C06D1DF20F53BED06D1D16510333F0E839A6F719A5D060DDF6E77794C0719EB723ABA2C07BDCDE6B25C073A97E9A0C00C247EBBEB73D0585E26A7E920F35B0EA2A3CB2077194F0799D3F632A8FD76D3D173D01D5D7683F2EF3A085E978FD1E179191406B5DF6E3A9A9D07D1DFF0561D0E7ACB417076D80D32BFE5'

CHARSET = '@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1BÆæßÉ !"#¤%&\'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà'

SPECIAL_CHARS = {  10: '\f', 20: '^', 40: '{', 41: '}', 47: '\\', 60: '[', 61: '~', 62: ']', 64: '|', 101: '€' }

TON = { 0: 'unknown', 1: 'international', 2: 'national', 3: 'specific', 4: 'subscriber', 5: 'alphanumeric', 6: 'abbreviated', 7: 'extended' }
NPI = { 0: 'unknown', 1: 'isdn', 2: 'data', 3: 'telex', 4: 'specific1', 5: 'specific2', 6: 'national', 7: 'private', 8: 'ermes', 9: 'extended' }
DCS = { 1: 'binary', 2: 'ucs2' }

class SMS_DELIVER:

    def __init__(self, pdu_string):
        smsc_len = int(pdu_string[:2], 16) * 2
        pdu_string = pdu_string[2+smsc_len:]
        pdu_header_int = int(pdu_string[:2], 16)
        self.tp_mms = self._get_bit(pdu_header_int, 2)
        self.tp_sri = self._get_bit(pdu_header_int, 5)
        self.tp_udhi = self._get_bit(pdu_header_int, 6)
        self.tp_rp = self._get_bit(pdu_header_int, 7)
        sender_num_len = int(pdu_string[2:4], 16)
        sender_num_type = int(pdu_string[4:6], 16)
        self.ton = TON[(sender_num_type & 0b01110000) >> 4]
        self.npi = NPI[(sender_num_type & 0b00001111)]
        self.sender_number_raw = pdu_string[6:6+sender_num_len]
        if self.ton == 'alphanumeric': 
            self.sender_number = self._decode(self._unpack_7bit(self.sender_number_raw, sender_num_len))
        else:
            self.sender_number = f'{self._octet_flip(pdu_string[6:6+sender_num_len])}'
        if self.ton == 'international':
            self.sender_number = f'+{self.sender_number}'
        pdu_string = pdu_string[6+sender_num_len:]
        self.tp_pid = pdu_string[:2]
        self.tp_dcs = DCS.get((int(pdu_string[2:4],16) & 0b1100) >> 2, 'gsm')
        timestamp_raw = pdu_string[4:18]
        self.timestamp = self._formatted_timestamp(self._octet_flip(timestamp_raw))
        self.tp_udl = int(pdu_string[18:20], 16)
        self.tp_ud = pdu_string[20:]
        if self.tp_udhi:
            self.tp_udhl = int(self.tp_ud[:2], 16)
            self.tp_udh = self.tp_ud[:2 + self.tp_udhl * 2]
            self.part = int(self.tp_udh[-2:], 16)
        else:
            self.tp_udhl = 0
            self.tp_udh = None
            self.part = 1
        self.message = self._decode_message()

    def _decode_message(self):
        message = ''
        if self.tp_dcs == 'gsm':
            tmp_message = self._unpack_7bit(self.tp_ud, self.tp_udl)
            message = self._decode(tmp_message[self.tp_udhl + (2 if self.tp_udhi > 0 else 0):])
        else:
            stride = 4 if self.tp_dcs == 'ucs2' else 2
            ud = self.tp_ud[self.tp_udhl * 2 + (2 if self.tp_udhi > 0 else 0):]
            for i in range(0, len(ud), stride):
                message += chr(int(ud[i:i+stride],16))
        return message
        
    def _formatted_timestamp(self, timestamp_raw):
        #return f'{timestamp_raw[4:6]}/{timestamp_raw[2:4]}/{timestamp_raw[:2]} {timestamp_raw[6:8]}:{timestamp_raw[8:10]}:{timestamp_raw[10:12]}'
        return f'20{timestamp_raw[:2]}-{timestamp_raw[2:4]}-{timestamp_raw[4:6]} {timestamp_raw[6:8]}:{timestamp_raw[8:10]}:{timestamp_raw[10:12]}'
        
    def _octet_flip(self, octet_string):
        flipped = ''
        for i in range(0, len(octet_string), 2):
            flipped += octet_string[i+1] + octet_string[i]
        if flipped[-1] == 'F':
            flipped = flipped[:-1]
        return flipped

    def _get_bit(self, value, bit_index):
        return (value >> bit_index) & 1

    def _unpack_7bit(self, packed, septet_count):
        octets = []
        for i in range(0, len(packed), 2):
            octet = packed[i:i+2]
            intval = int(octet,16)
            octets.append(intval)
        septets = []
        shift = 0
        buffer = 0
    
        for b in octets:
            buffer |= b << shift
            shift += 8
            while shift >= 7 and len(septets) < septet_count:
                septets.append(buffer & 0x7F)
                buffer >>= 7
                shift -= 7
    
        return septets

    def _decode(self, septets):
        op = ''
        ext=False
        for s in septets:
            if s == 0x1B:
                ext=True
                continue
            else:
                if ext == True:
                    op += SPECIAL_CHARS[s]
                    ext = False
                else:
                    op += CHARSET[s]
        return op
    