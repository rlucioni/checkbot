# checkbot

Bot for checking Hmart points

## Quickstart

This project uses [Zappa](https://github.com/Miserlou/Zappa) to deploy a simple Python application to [AWS Lambda](https://aws.amazon.com/lambda/). If you haven't already, create a local [AWS credentials file](https://aws.amazon.com/blogs/security/a-new-and-standardized-way-to-manage-credentials-in-the-aws-sdks/).

Install requirements:

    $ make requirements

Package and deploy the service:

    $ make deploy

Finally, set environment variables the app needs to function. These include connection details for an external Redis instance. You can use a service like [ElastiCache](https://aws.amazon.com/elasticache/redis/) or [Redis Labs](https://redislabs.com/) for this.

If you make a change and want to deploy again:

    $ make ship

## Development

checkbot is a Python script. It can be run locally without using Lambda. First, start Redis using Docker Compose:

    $ docker-compose up -d

Run checkbot:

    $ make checkbot

Run the linter:

    $ make lint

Run tests:

    $ make test
