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

"""Configuration module for the application.

Handles loading settings from Environment Variables (injected by Cloud Run).
Leverages Pydantic for data validations.
"""

import logging
from app.core.log_setup import setup_logging
from cryptography.fernet import Fernet
import pydantic
import pydantic_settings

# Ensure logging is configured before the configuration loads.
setup_logging()
logger = logging.getLogger(__name__)


class Settings(pydantic_settings.BaseSettings):
  """Centralized application configuration and secrets management.

  The class defines the schema for Environment Variables required by the
  application.
  It leverages Pydantic for strict type validation, security checks (e.g.,
  Fernet key verification),
  and dynamic property computation.

  Configuration Loading Precedence:
      1. Environment Variables (injected by Cloud Run or OS).
      2. .env file (for local development).

  Attributes:
      GOOGLE_CLIENT_ID (str): OAuth Client ID from GCP.
      GOOGLE_CLIENT_SECRET (str): OAuth Client Secret from GCP.
      GOOGLE_ADS_DEVELOPER_TOKEN (str): Token for Google Ads API access.
      PROJECT_ID (str): GCP Project ID.
      DATASET_ID (str): BigQuery Dataset ID.
      ANALYSIS_TABLE_ID (str): BigQuery Table ID for Analysis.
      STATUS_TABLE_ID (str): BigQuery Table ID for Status.
      STATUS_VIEW_ID (str): BigQuery View ID for Status.
      SESSION_SECRET_KEYS (str): Comma-separated list of Fernet keys for session
        encryption.
      ENVIRONMENT (str): Operational context (e.g., 'local' and 'production').
      LB_DOMAIN (str): Public domain of the Backend Load Balancer (e.g.,
        api.example.com).
      FRONTEND_URL (str): Public origin of the Angular frontend (used for CORS).

  Computed Properties:
      is_production (bool): True if running in production mode.
      protocol (str): 'https' for production, 'http' otherwise.
      redirect_uri (str): The constructed OAuth callback URL.
      cors_origins (list[str]): List of allowed CORS origins, auto-configured
        based on environment.
  """

  # Secrets (Loaded from Environment Variables, populated by Secret Manager).
  # Note: Using Field() makes this description visible in Swagger/OpenAPI.
  # The fields marked with elipsis '...' are the required ones.
  # BigQuery Configuration
  GOOGLE_CLIENT_ID: str = pydantic.Field(
      ..., description="OAuth Client ID, generated using GCP Credentials."
  )
  GOOGLE_CLIENT_SECRET: str = pydantic.Field(
      ..., description="OAuth Client Secret, generated using GCP Credentials."
  )
  GOOGLE_ADS_DEVELOPER_TOKEN: str = pydantic.Field(
      ...,
      description=(
          "API Token for Google Ads API generated through Google Ads Manager"
          " Account."
      ),
  )
  GOOGLE_ADS_CUSTOMER_ID: str = pydantic.Field(
      default="",
      description="Default Google Ads Customer ID to use if not specified.",
  )
  PROJECT_ID: str = pydantic.Field(..., description="GCP Project ID.")
  DATASET_ID: str = pydantic.Field(..., description="BigQuery Dataset ID.")
  VIDEO_ANALYSIS_TABLE_ID: str = pydantic.Field(
      ..., description="BigQuery Table ID for Analysis."
  )
  MATCHED_PRODUCTS_TABLE_ID: str = pydantic.Field(
      ..., description="BigQuery Table ID for Matched Products."
  )
  MATCHED_PRODUCTS_VIEW_ID: str = pydantic.Field(
      ..., description="BigQuery View ID for Matched Products."
  )
  CANDIDATE_STATUS_TABLE_ID: str = pydantic.Field(
      ..., description="BigQuery Table ID for Candidate Status."
  )
  CANDIDATE_STATUS_VIEW_ID: str = pydantic.Field(
      ..., description="BigQuery View ID for Latest Candidate Status."
  )
  LATEST_PRODUCTS_TABLE_ID: str = pydantic.Field(
      ..., description="BigQuery Table ID for Latest Products."
  )

  GOOGLE_ADS_INSERTION_REQUESTS_TABLE_ID: str = pydantic.Field(
      ..., description="BigQuery Table ID for Google Ads Insertion Requests."
  )
  AD_GROUP_INSERTION_STATUS_TABLE_ID: str = pydantic.Field(
      ..., description="BigQuery Table ID for Ad Group Insertion Status."
  )
  SESSION_SECRET_KEYS: str = pydantic.Field(
      ...,
      description=(
          "Comma separated string of Fernet Keys for Encrypting/Decrypting"
          " Session Cookies. The same is required for MultiFernet"
          " implementation in order to support rotation of the Fernet Keys. The"
          " newest key should be supplied at the first index."
      ),
  )

  # Infrastructure configuration.
  ENVIRONMENT: str = pydantic.Field(
      ...,
      description=(
          "Operational environment (e.g., 'local' or 'production'). Controls"
          " security flags."
      ),
  )
  LB_DOMAIN: str = pydantic.Field(
      ..., description="The Public IP/Domain of the Backend Load Balancer."
  )
  FRONTEND_URL: str = pydantic.Field(
      ...,
      description=(
          "The URL where the Angular Frontend is hosted. The URL is also"
          " leveraged for CORS allowlisting and Post-Login redirection."
      ),
  )

  # --- Computed Properties ---

  @property
  def _is_production(self) -> bool:
    """Determines if the current environment is production.

    Returns:
        bool: True if ENVIRONMENT is 'production', else False.
    """
    return self.ENVIRONMENT.lower() == "production"

  @pydantic.computed_field
  def is_production(self) -> bool:
    """Computed field for the determining if the current environment is production.

    Returns:
        bool: True if ENVIRONMENT is 'production', else False.
    """
    return self._is_production

  @pydantic.computed_field
  def protocol(self) -> str:
    """Determines the protocol based on the environment security requirements.

    Returns:
        str: 'https' for production, 'http' for local/dev.
    """
    return "https" if self._is_production else "http"

  @pydantic.computed_field
  def redirect_uri(self) -> str:
    """Constructs the OAuth callback URI based on the Load Balancer Domain.

    Returns:
        str: The fully qualified callback URL.
    """
    return f"{self.protocol}://{self.LB_DOMAIN}/api/auth/callback"

  @pydantic.computed_field
  def cors_origins(self) -> list[str]:
    """Constructs the list of allowed CORS origins.

    Returns:
        List[str]: A list containing the Frontend URL and local dev fallback.
    """
    origins = [self.FRONTEND_URL]

    # Only allow localhost in non-production environments.
    if not self._is_production:
      origins.append("http://localhost:4200")

    return origins

  # --- Validators ---
  @pydantic.field_validator("SESSION_SECRET_KEYS")
  @classmethod
  def validate_keys(cls, v: str) -> str:
    """Validates that the session keys string is not empty.

    Args:
        v (str): The raw comma-separated string of keys.

    Returns:
        str: The validated string.

    Raises:
        ValueError: If the string is empty or contains no keys.
    """
    keys = [k.strip() for k in v.split(",") if k.strip()]
    if not keys:
      logger.critical("No session keys provided in configuration.")
      raise ValueError("At least one session key is required.")

    # Verify keys are valid Fernet tokens immediately.
    for i, k in enumerate(keys):
      try:
        Fernet(k)
      except Exception as e:
        logger.error("Invalid Fernet key at index %s: %s", i, str(e))
        raise ValueError(
            f"Invalid Fernet key detected: {k[:5]}... Error: {e}"
        ) from e

    logger.info(
        "Successfully loaded '%s' session keys for rotation.", len(keys)
    )
    return ",".join(keys)  # Return the sanitized string of Fernet Keys.

  @pydantic.field_validator("LB_DOMAIN", "FRONTEND_URL")
  @classmethod
  def strip_trailing_slash(cls, url: str) -> str:
    """Strips the trailing forward slash ('/') from the end.

    Used to validate 'LB_DOMAIN' and 'FRONTEND_URL'.

    Args:
        url (str): URL that needs to be checked for trailing forward slash
          ('/').

    Returns:
        str: Sanitized URL with trailing forward slash ('/') removed.
    """
    return url.rstrip("/")

  # Configuration for loading '.env' files (prioritizes Environment Variables).
  model_config = pydantic_settings.SettingsConfigDict(
      env_file=".env", extra="ignore"
  )


# Initialize settings (Triggers validation and logging).
try:
  # Singleton instance for import across the application.
  settings = Settings()  # type: ignore
  logger.info(
      "Configuration loaded for environment: '%s'", settings.ENVIRONMENT
  )
  logger.info("Allowed CORS Origins: '%s'", settings.cors_origins)
except Exception as e:
  logger.critical("Failed to load application configuration: '%s'", str(e))
  raise
