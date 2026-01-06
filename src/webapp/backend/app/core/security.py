# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Security module for handling encryption and decryption of Session Tokens."""

import logging

from app.core.config import settings

from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
from cryptography.fernet import MultiFernet

logger = logging.getLogger(__name__)


def _get_cipher_suite() -> MultiFernet:
  """Initializes the MultiFernet suite from configured keys.

  Returns:
    A MultiFernet cipher suite.

  Raises:
    Exception: If initialization fails.
  """
  try:
    keys = [
        k.strip() for k in settings.SESSION_SECRET_KEYS.split(",") if k.strip()
    ]
    logger.info("Initializing Cipher Suite with '%d' keys.", len(keys))
    return MultiFernet([Fernet(k.encode()) for k in keys])
  except Exception:
    logger.exception("Failed to initialize Cipher Suite")
    raise


_cipher = _get_cipher_suite()


def encrypt_token(token: str) -> str:
  """Encrypts a plain text string using the primary (first) key.

  Args:
    token: The plain text token to encrypt.

  Returns:
    The encrypted token as a string.

  Raises:
    Exception: If encryption fails.
  """
  try:
    encrypted = _cipher.encrypt(token.encode()).decode()
    logger.debug("Token encrypted successfully using primary key.")
    return encrypted
  except Exception:
    logger.exception("Encryption failed")
    raise


def decrypt_token(encrypted_token: str) -> str:
  """Attempts to decrypt a cipher text string using all available keys.

  Args:
    encrypted_token: The encrypted token to decrypt.

  Returns:
    The decrypted token as a plain text string.

  Raises:
    InvalidToken: If decryption fails due to invalid token.
    Exception: For unexpected decryption errors.
  """
  try:
    decrypted = _cipher.decrypt(encrypted_token.encode()).decode()
    logger.debug("Token decrypted successfully.")
    return decrypted
  except InvalidToken:
    logger.warning(
        "Decryption failed: Invalid Token (Signature mismatch or expired)."
    )
    raise
  except Exception:
    logger.exception("Unexpected decryption error")
    raise
