# Forest

A slack app built with AWS [SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html)

## Building and deployment

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

