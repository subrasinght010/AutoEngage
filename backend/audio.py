class AudioBuffer:
    def __init__(self, chunk_size=2048):
        self.chunk_size = chunk_size
        self.buffer = bytearray()

    def add_data(self, data: bytes):
        self.buffer.extend(data)

    def get_chunks(self):
        chunks = []
        while len(self.buffer) >= self.chunk_size:
            chunks.append(self.buffer[:self.chunk_size])
            self.buffer = self.buffer[self.chunk_size:]
        return chunks

    def flush(self):
        if self.buffer:
            flushed = bytes(self.buffer)
            self.buffer.clear()
            return flushed
        return None
