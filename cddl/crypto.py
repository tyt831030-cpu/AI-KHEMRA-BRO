"""AES-128 segment decryption as defined by the HLS specification.

This module implements *only* ``METHOD=AES-128``: a symmetric key fetched over
HTTPS and applied in CBC mode.  That is the classic, non-DRM HLS encryption
used by ordinary web VOD.  DRM schemes (SAMPLE-AES, Widevine, FairPlay,
PlayReady) are explicitly out of scope and rejected upstream in :mod:`cddl.hls`.
"""
from __future__ import annotations

import threading
from typing import Mapping, Optional

from .hls import Key

AES_BLOCK_SIZE = 16

try:  # pragma: no cover - exercised implicitly by the test-suite
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    _HAVE_CRYPTOGRAPHY = True
except ImportError:  # pragma: no cover
    _HAVE_CRYPTOGRAPHY = False


class DecryptionError(RuntimeError):
    """Raised when a segment cannot be decrypted."""


def iv_from_sequence(sequence: int) -> bytes:
    """Derive the IV for a segment when ``#EXT-X-KEY`` omits the ``IV`` attribute.

    RFC 8216: the IV is the segment's media sequence number, big-endian, padded
    on the left with zeroes to 128 bits.
    """
    if sequence < 0:
        raise ValueError("sequence must be non-negative")
    return sequence.to_bytes(AES_BLOCK_SIZE, "big")


class KeyStore:
    """Fetches and caches AES keys, one fetch per distinct key URI."""

    def __init__(self, session) -> None:
        self._session = session
        self._cache: dict[str, bytes] = {}
        self._lock = threading.Lock()

    def key_bytes(self, key: Key) -> bytes:
        if key.uri is None:
            raise DecryptionError("AES-128 key tag has no URI")
        with self._lock:
            cached = self._cache.get(key.uri)
        if cached is not None:
            return cached

        data = self._session.get_bytes(key.uri)
        if len(data) not in (16, 24, 32):
            raise DecryptionError(
                f"key at {key.uri} is {len(data)} bytes; expected 16 (AES-128)"
            )
        with self._lock:
            self._cache[key.uri] = data
        return data

    def preload(self, keys: list[Key]) -> None:
        """Fetch every distinct key up-front so workers never race on the network."""
        seen: set[str] = set()
        for key in keys:
            if key and key.uri and key.uri not in seen:
                seen.add(key.uri)
                self.key_bytes(key)


def decrypt_aes128_cbc(payload: bytes, key: bytes, iv: bytes) -> bytes:
    """Decrypt one AES-128-CBC segment, tolerating PKCS#7 padding."""
    if not _HAVE_CRYPTOGRAPHY:
        raise DecryptionError(
            "the 'cryptography' package is required to decrypt AES-128 HLS segments "
            "(pip install cryptography)"
        )
    if len(key) != 16:
        raise DecryptionError(f"AES-128 needs a 16-byte key, got {len(key)}")
    if len(iv) != AES_BLOCK_SIZE:
        raise DecryptionError(f"IV must be 16 bytes, got {len(iv)}")
    if len(payload) % AES_BLOCK_SIZE:
        raise DecryptionError(
            f"ciphertext length {len(payload)} is not a multiple of the AES block size"
        )

    decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    plain = decryptor.update(payload) + decryptor.finalize()

    # Strip PKCS#7 padding when it is well formed.  Many HLS packagers pad with
    # an H.264/AAC "AUD" NAL or zeroes instead, so an invalid pad is left alone.
    pad = plain[-1] if plain else 0
    if 1 <= pad <= AES_BLOCK_SIZE and plain[-pad:] == bytes([pad]) * pad:
        plain = plain[:-pad]
    return plain


def decrypt_segment(payload: bytes, key: Optional[Key], key_bytes: Optional[bytes], sequence: int) -> bytes:
    """Decrypt a segment payload according to its key tag (no-op if unencrypted)."""
    if key is None or key.is_none:
        return payload
    if not key.is_aes128:
        raise DecryptionError(f"unsupported METHOD={key.method}")
    if key_bytes is None:
        raise DecryptionError("AES-128 segment is missing its key material")
    iv = key.iv or iv_from_sequence(sequence)
    return decrypt_aes128_cbc(payload, key_bytes, iv)


def distinct_keys(mapping: Mapping[int, Optional[Key]]) -> list[Key]:
    """Deduplicate key tags by URI for a preload pass."""
    out: list[Key] = []
    seen: set[str] = set()
    for key in mapping.values():
        if key and key.uri and key.uri not in seen:
            seen.add(key.uri)
            out.append(key)
    return out