# coding: utf-8
#
# This code is part of asarlib.
#
# Copyright (c) 2022, Dylan Jones

import os
import sys
import json
import struct

if sys.platform == "win32":
    ENCODING = "ANSI"
elif sys.platform == "darwin":
    ENCODING = "cp437"
else:
    ENCODING = "utf-8"


class AsarFileHeaderError(KeyError):
    pass


class AsarFile:

    def __init__(self, file=None, mode="rb", encoding=None):
        self._encoding = encoding or ENCODING
        self._content_offset = 0
        self._fh = None

        self.files = dict()
        if file is not None:
            self.open(file, mode)

    @property
    def encoding(self):
        return self._encoding

    def open(self, file, mode="r"):
        """Open an Asar file.

        Parameters
        ----------
        file : str
            The file path of the Asar file to open.
        mode : {'r', 'w'}
            The mode for opening the Asar file.
        """
        # Open the file handler
        mode = mode.rstrip("b")
        if mode == "w":
            raise NotImplementedError("Writing Asar files is not yet supported!")
        self._fh = open(file, f"{mode}b")

        # Parse the Asar file tags:
        # The Asar files use Google's pickle format which prefixes each field
        # with its total length. The first 4 bytes is a 32-bit unsigned integer
        # _encoding the length of the ``len_header`` field (always 4).
        # The following 4 bytes is the 32-bit unsigned int ``len_header``, which
        # specifies the number of bytes in the Asar header.
        len_size, len_header = struct.unpack("II", self._fh.read(8))
        assert len_size == 4

        # The pickle format uses 8 bytes padding for each field, so the header start.
        # With the first 4 bytes the header starts at:
        header_start = 12 + len_size
        len_header -= 8  # Subtract 8 bytes padding

        # Read the actual Asar header.
        # The header is a JSON string storing the information about the contents in the
        # ASAR file.
        self._fh.seek(header_start)
        header_data: bytes = self._fh.read(len_header)  # noqa
        if header_data.endswith(b"\x00"):
            header_data = header_data.rstrip(b"\x00")
        self.files = json.loads(header_data.decode(self._encoding))

        # Store start of content (after header)
        self._content_offset = header_start + len_header

    def close(self):
        """Closes the Asar file if it is still open."""
        if self._fh is not None:
            self._fh.close()
            self._fh = None
            self._content_offset = 0
            self.files.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def seek(self, pos=0):
        """Seeks a position in the Asar file content, starting after the header.

        Parameters
        ----------
        pos : int, optional
            The position in the Asar content section to set the file pointer to.
            Note that this is not the actual position in the Asar file, but the
            position in the content section (after the header) in the Asar file.
            Passing ``pos=0`` sets the file pointer to the start of the content section.
        """
        self._fh.seek(self._content_offset + int(pos))

    def tell(self):
        return self._fh.tell() - self._content_offset

    def read(self, n=None, decode=True, encoding=None):
        data = self._fh.read(n)
        if decode:
            data = data.decode(encoding or self.encoding)
        return data

    # ==================================================================================

    def get_header(self, path="", keep_files=False):
        if not path:
            return self.files["files"]
        root, name = os.path.split(path)
        keys = [name]
        while root:
            root, name = os.path.split(root)
            keys.append(name)
        keys = keys[::-1]
        parent = self.files["files"]
        for key in keys[:-1]:
            parent = parent[key]["files"]
        item = parent[keys[-1]]
        if keep_files:
            return item
        return item.get("files", item)

    def walk(self, root=""):
        root_item = self.get_header(root)
        parents = [(root, root_item)]
        while parents:
            new_parents = list()
            for root, parent in parents:
                dirs, files = list(), list()
                for name, content in parent.items():
                    if "files" in content:
                        dirs.append(name)
                        new_parents.append((os.path.join(root, name), content["files"]))
                    else:
                        files.append(name)
                yield root, dirs, files
            parents = new_parents

    def listdir(self, root=""):
        parent = self.get_header(root)
        yield from parent.keys()

    def walk_files(self, root=""):
        for _root, _, files in self.walk(root):
            yield _root, files

    # ==================================================================================

    def read_file(self, path, decode=True, encoding=None):
        header = self.get_header(path)
        try:
            offset = int(header["offset"])
            size = int(header["size"])
        except KeyError as e:
            raise AsarFileHeaderError(f"Could not read file '{path}': {e}")
        self.seek(offset)
        return self.read(size, decode, encoding)

    def extract_file(self, path, dst_dir=""):
        data = self.read_file(path, decode=False)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        dst_path = os.path.join(dst_dir, os.path.split(path)[1])
        with open(dst_path, "wb") as fh:
            fh.write(data)

    def extract(self, root="", dst_dir=""):
        if not dst_dir:
            dst_dir = "asar_content"
        errors = list()
        for _root, files in self.walk_files(root):
            dst = os.path.join(dst_dir, _root)
            for name in files:
                try:
                    self.extract_file(os.path.join(_root, name), dst_dir=dst)
                except AsarFileHeaderError as e:
                    errors.append(e)
        return errors

    # ==================================================================================

    def __repr__(self):
        return f"{self.__class__.__name__}()"

    def treestr(self, root="", indent=3, depth=None, _lvl=0, _name="", _item=None):
        if root:
            name = root
            item = self.get_header(root, keep_files=True)
        else:
            name = self.__str__() if _lvl == 0 else _name
            item = _item or self.files

        vline = "│" + " " * max(indent - 1, 1)
        hline = "├" + "─" * max(indent - 2, 0) + " "
        if _lvl == 0:
            s = f"{name}\n"
        else:
            s = vline * (_lvl - 1) + f"{hline}{_name}\n"
        if depth is None or _lvl < depth:
            if "files" in item:
                for key, val in item["files"].items():
                    s += self.treestr(
                        indent=indent,
                        depth=depth,
                        _lvl=_lvl + 1,
                        _name=key,
                        _item=val
                    )
        return s
