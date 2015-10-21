# File: intc.py

if hasattr(int, 'to_bytes'):
    
    def to_bytes(n, length, byteorder='big'):
        return n.to_bytes(length, byteorder)
    
    def from_bytes(bytes, byteorder='big'):
        return int.from_bytes(bytes, byteorder)
    
else:
    
    def to_bytes(n, length, byteorder='big'):
        h = '%x' % n
        s = ('0'*(len(h) % 2) + h).zfill(length*2).decode('hex')
        return s if byteorder == 'big' else s[::-1]
    
    def from_bytes(bytes, byteorder='big'):
        assert byteorder == 'big'
        
        ret = long(0)
        for b in bytes:
            ret <<= 8
            ret += ord(b)
        return ret

