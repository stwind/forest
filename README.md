# Forest

A slack app built with AWS [SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html)

## Requirements

* [pyenv](https://github.com/pyenv/pyenv)
* [aws-sam-cli](https://github.com/awslabs/aws-sam-cli)

## Building and deployment

```sh
$ pyenv install 3.7.2
$ pyenv virtualenv 3.7.2 forest
$ pyenv activate forest

$ pip install --upgrade pip pip-tools pipdeptree fabric
```

### Making Release

To build a python wheel package and generate `requirements.txt` for later usage

```sh
$ fab freeze
```

### Building SAM package

To build a AWS SAM package

```sh
$ fab build
```

### Deploying to AWS

```sh
$ fab deploy
```

## Testing

```sh
$ python setup.py test
```

