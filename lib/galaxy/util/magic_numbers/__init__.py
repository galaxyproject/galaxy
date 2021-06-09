import os
import io

# The number of bytes to be read from a file/stream when searching for a
# magic number.  No magic number is even close to this long, but given most
# block devices read 4K chunks this is likely a moot point.
BLOCK_SIZE=1024


class MagicNumber:
    '''
    Information about magic numbers loaded from the tsv and text data files.
    '''
    def __init__(self, number, extension, description):
        self.number = number
        self.bytes = [ int(hex, 16) for hex in number.split() if hex != '??']
        self.extension = extension.strip()
        self.description = description.strip()


class TrieNode:
    '''
    A node in the search tree.

    If the formats list is not empty then the sequence of bytes that led to this
    node is a known magic number.
    '''
    def __init__(self):
        self.children = [None] * 256
        self.formats = []


class MagicNumberSniffer:
    '''
    The prefix search tree (trie) used to identify magic numbers at
    the start of a file.
    '''
    def __init__(self):
        self.root = TrieNode()
        this_dir = os.path.dirname(__file__)
        with open(os.path.join(this_dir, "magic-numbers.tsv")) as fp:
            for line in fp.readlines():
                parts = line.split('\t')
                number = MagicNumber(*parts)
                self.add(number)
        with open(os.path.join(this_dir, "magic-numbers.txt")) as fp:
            for line in fp.readlines():
                parts = line.split('\t')
                bytes = ' '.join([ hex(ord(c)).replace('0x', '') for c in parts[0]])
                number = MagicNumber(bytes, parts[1], parts[2])
                self.add(number)


    def add(self, number: MagicNumber):
        index = 0
        current = self.root
        while index < len(number.bytes):
            next = number.bytes[index]
            if current.children[next] is None:
                trie = TrieNode()
                current.children[next] = trie
            else:
                trie = current.children[next]
            current = trie
            index += 1
        current.formats.append(number)


    def sniff(self, path, isFile=True):
        if isFile:
            with open(path, 'rb') as f:
                buff = f.read(BLOCK_SIZE)
        else:
            f = io.BytesIO(path)
            buff = f.read(BLOCK_SIZE)

        p = 0  # pointer into the above buffer

        # Walk the search tree using the bytes in `buff` as the indices.
        current = self.root
        while current is not None:
            b = buff[p]
            p += 1
            if b == '':
                # EOF
                break
            # print(f"ch: {hex(b)}")
            child = current.children[b]
            if child is None:
                break
            current = child

        if current is None:
            return []
        return current.formats


__all__ = [ 'MagicNumberSniffer', 'MagicNumber' ]
