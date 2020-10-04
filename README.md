# aws_2fa

Manage and update aws-cli 2fa credentials.


# Installation

Simply run:

    $ pip3 install aws_2fa


# Usage

To use it:

```
$ aws-2fa --help
Usage: aws-2fa [OPTIONS] TOKEN [SERIAL_NUMBER] [DURATION]

  Manage and update aws-cli 2fa credentials

Options:
  -p, --profile TEXT        The profile to be updated with the 2fa
                            credentials. Default: default
  --credential-path PATH    AWS credentials file path. Default:
                            ~/.aws/credentials
  --print-credentials TEXT  Print the generated credentials
  --help                    Show this message and exit.

```

Example:

The first time you run the command the serial number of your 2fa device should be provided and it's stored on your credentials file

	$ aws-2fa 118966 arn:aws:iam::0000000000:mfa/test

Then you can simply run the command with the 2fa token to update the credentials

	$ aws-2fa 118966
