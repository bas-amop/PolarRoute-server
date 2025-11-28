import logging
import os


class GroupWriteRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """A rotating file handler which allows group write permissions."""

    def _open(self):
        # Open the file using the standard method
        stream = super()._open()

        # Explicitly change permissions to 664 (rw-rw-r--)
        # 0o664 is the octal representation
        try:
            os.chmod(self.baseFilename, 0o664)
        except OSError:
            # Handle cases where the process isn't the owner (rare in proper setups)
            pass

        return stream
