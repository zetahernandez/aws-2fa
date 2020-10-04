import configparser
import os
from typing import Any, Dict, Optional

import boto3
import click

PROFILE_SUFFIX = '2fa'
DEFAULT_TOKEN_DURATION = 36*60*60  # 36 hours to seconds

CONF_KEY_AWS_ACCESS_KEY_ID = 'aws_access_key_id'
CONF_KEY_AWS_SECRET_ACCESS_KEY = 'aws_secret_access_key'
CONF_KEY_AWS_SESSION_TOKEN = 'aws_session_token'
CONF_KEY_AWS_SERIAL_NUMBER = 'aws_serial_number'


def get_client(aws_access_key_id: Optional[str] = None, aws_secret_access_key: Optional[str] = None):
    return boto3.client('sts', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)


class AWSConfig:
    def __init__(self, profile: str, credential_path: Optional[str] = None) -> None:
        self.profile = profile
        self.credential_path = credential_path

        self.config = configparser.ConfigParser()
        self.config.read(self.credential_path)

        if self.profile not in self.config.sections():
            raise click.ClickException(f'Profile {self.profile} not found on {self.credential_path}')

    @property
    def aws_access_key_id(self) -> str:
        return self.config[self.profile].get(CONF_KEY_AWS_ACCESS_KEY_ID)

    @property
    def aws_secret_access_key(self) -> str:
        return self.config[self.profile].get(CONF_KEY_AWS_SECRET_ACCESS_KEY)

    @property
    def profile_2fa(self) -> str:
        return f'{self.profile}_{PROFILE_SUFFIX}'

    @property
    def serial_number(self) -> Optional[str]:
        if self.profile_2fa not in self.config.sections():
            return None

        return self.config[self.profile_2fa].get(CONF_KEY_AWS_SERIAL_NUMBER)

    def set_2fa_credentials(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_session_token: str,
        serial_number: Optional[str] = None,
    ):
        if self.profile_2fa not in self.config.sections():
            self.config.add_section(self.profile_2fa)
            click.echo(f'The profile `{self.profile_2fa}` was created on your credential file')

        self.config[self.profile_2fa][CONF_KEY_AWS_ACCESS_KEY_ID] = aws_access_key_id
        self.config[self.profile_2fa][CONF_KEY_AWS_SECRET_ACCESS_KEY] = aws_secret_access_key
        self.config[self.profile_2fa][CONF_KEY_AWS_SESSION_TOKEN] = aws_session_token
        if serial_number is not None:
            self.config[self.profile_2fa][CONF_KEY_AWS_SERIAL_NUMBER] = serial_number

        with open(self.credential_path, 'w') as configfile:
            self.config.write(configfile)


class GetSessionToken:
    def __init__(self, client: Any, aws_config: AWSConfig) -> None:
        self.client = client
        self.aws_config = aws_config

    def get_session_token(
            self,
            token=str,
            duration: Optional[int] = None,
            serial_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        serial_number = serial_number or self.aws_config.serial_number
        if serial_number is None:
            raise click.ClickException(
                f'A 2fa device id needs to be provided at least once for profile {self.aws_config.profile}'
            )

        response = self.client.get_session_token(
            DurationSeconds=duration or DEFAULT_TOKEN_DURATION,
            SerialNumber=serial_number,
            TokenCode=token,
        )
        return response


@click.command()
@click.option('--profile', default='default', envvar='AWS_PROFILE', required=False)
@click.option(
    '--credential-path',
    type=click.Path(exists=True),
    required=False,
    default=os.path.expanduser('~/.aws/credentials'),
    help='AWS credentils file path',
)
@click.option('-p', '--print-credentials', default=False, help='Print the generated creedentials')
@click.argument('token', required=True)
@click.argument('serial_number', required=False)
@click.argument('duration', required=False)
def main(token, duration, credential_path, profile, serial_number, print_credentials):
    """Manage and update aws-cli 2fa creedentials"""
    aws_config = AWSConfig(profile=profile, credential_path=credential_path)
    client = get_client(
        aws_access_key_id=aws_config.aws_access_key_id,
        aws_secret_access_key=aws_config.aws_secret_access_key,
    )
    session_token = GetSessionToken(
        client=client,
        aws_config=aws_config
    ).get_session_token(
        token=token,
        duration=duration,
        serial_number=serial_number,
    )

    aws_config.set_2fa_credentials(
        aws_access_key_id=session_token['Credentials']['AccessKeyId'],
        aws_secret_access_key=session_token['Credentials']['SecretAccessKey'],
        aws_session_token=session_token['Credentials']['SessionToken'],
        serial_number=serial_number,
    )

    expires_at = session_token['Credentials']['Expiration']
    click.echo(
        f"""
        The AWS session credentials were successfully updated for
        profile {aws_config.profile_2fa}, expires at {expires_at}
        """)

    if print_credentials:
        print(session_token)
