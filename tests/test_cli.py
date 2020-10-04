from datetime import datetime

import pytest
from click.testing import CliRunner

from aws_2fa import cli


DEFAULT_CREDENTIALS = """[default]
aws_access_key_id = AAAAAAAAAAAAAAAAAAAA
aws_secret_access_key = xxxxxxxxxxxxxxxxxxxxxx/xxxxxxxxxxxxx

[prod]
aws_access_key_id = AAAAAAAAAAAAAAAAAAAA
aws_secret_access_key = xxxxxxxxxxxxxxxxxxxxxx/xxxxxxxxxxxxx

"""

EXPECTED_CREDENTIALS = """[default]
aws_access_key_id = AAAAAAAAAAAAAAAAAAAA
aws_secret_access_key = xxxxxxxxxxxxxxxxxxxxxx/xxxxxxxxxxxxx

[prod]
aws_access_key_id = AAAAAAAAAAAAAAAAAAAA
aws_secret_access_key = xxxxxxxxxxxxxxxxxxxxxx/xxxxxxxxxxxxx

[default_2fa]
aws_access_key_id = FAKE_ACCESS_KEY_ID
aws_secret_access_key = FAKE_SECRET_ACCESS_KEY
aws_session_token = FAKE_SESSION_TOKEN
aws_serial_number = arn:aws:iam::000000000:mfa/test

"""

EXPECTED_CREDENTIALS_PROD = """[default]
aws_access_key_id = AAAAAAAAAAAAAAAAAAAA
aws_secret_access_key = xxxxxxxxxxxxxxxxxxxxxx/xxxxxxxxxxxxx

[prod]
aws_access_key_id = AAAAAAAAAAAAAAAAAAAA
aws_secret_access_key = xxxxxxxxxxxxxxxxxxxxxx/xxxxxxxxxxxxx

[prod_2fa]
aws_access_key_id = FAKE_ACCESS_KEY_ID
aws_secret_access_key = FAKE_SECRET_ACCESS_KEY
aws_session_token = FAKE_SESSION_TOKEN
aws_serial_number = arn:aws:iam::000000000:mfa/test

"""


@pytest.fixture
def mock_sts_client(mocker):
    yield mocker.patch('aws_2fa.cli.get_client').return_value


@pytest.fixture(autouse=True)
def mock_get_session_tocken(mock_sts_client):
    mock_sts_client.get_session_token.return_value = {
        'Credentials': {
            'AccessKeyId': 'FAKE_ACCESS_KEY_ID',
            'SecretAccessKey': 'FAKE_SECRET_ACCESS_KEY',
            'SessionToken': 'FAKE_SESSION_TOKEN',
            'Expiration': datetime(2021, 1, 1),
        }
    }
    return mock_sts_client.get_session_token


@pytest.fixture
def default_credentials(tmpdir):
    p = tmpdir.mkdir('.aws').join('credentials')
    p.write(DEFAULT_CREDENTIALS)
    yield p


@pytest.fixture
def default_credentials_with_2fa(tmpdir):
    p = tmpdir.mkdir('.aws').join('credentials')
    p.write(EXPECTED_CREDENTIALS)
    yield p


@pytest.fixture
def runner():
    return CliRunner()


def test_default_profile(runner, default_credentials, mock_sts_client):
    runner.invoke(
        cli.main,
        [f'--credential-path={default_credentials}', '12345', 'arn:aws:iam::000000000:mfa/test']
    )

    assert default_credentials.read() == EXPECTED_CREDENTIALS
    mock_sts_client.get_session_token.assert_called_once_with(
        DurationSeconds=129600,
        SerialNumber='arn:aws:iam::000000000:mfa/test',
        TokenCode='12345',
    )


def test_prod_profile(runner, default_credentials, mock_sts_client):
    runner.invoke(
        cli.main,
        [f'--credential-path={default_credentials}', '--profile=prod',  '12345', 'arn:aws:iam::000000000:mfa/test']
    )

    assert default_credentials.read() == EXPECTED_CREDENTIALS_PROD
    mock_sts_client.get_session_token.assert_called_once_with(
        DurationSeconds=129600,
        SerialNumber='arn:aws:iam::000000000:mfa/test',
        TokenCode='12345',
    )


def test_default_profile_update(runner, default_credentials_with_2fa, mock_sts_client):
    runner.invoke(
        cli.main,
        [f'--credential-path={default_credentials_with_2fa}',  '12345']
    )

    assert default_credentials_with_2fa.read() == EXPECTED_CREDENTIALS
    mock_sts_client.get_session_token.assert_called_once_with(
        DurationSeconds=129600,
        SerialNumber='arn:aws:iam::000000000:mfa/test',
        TokenCode='12345',
    )
