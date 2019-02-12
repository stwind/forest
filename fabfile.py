from fabric import task, Connection


def run(c, cmd):
    c.run(cmd, replace_env=False, echo=True)


@task
def freeze(c):
    run(c, 'python setup.py release')
    run(c, "pip-compile -f dist --output-file requirements.txt - <<< 'forest'")
    run(c, "awk -i inplace 'BEGINFILE{print \"-f dist\"} {print $0}' requirements.txt")


@task
def build(c):
    run(c, 'sam build -t sam/template.yml -m requirements.txt')
    run(c, 'find .aws-sam/build/ -name "*-info" -type d -exec rm -rf {} +')
    run(c, 'find .aws-sam/build/ -type d \( -name "boto3*" -o -name "botocore*" -o -name "docutils*" -o -name "jmespath*" -o -name "python-dateutil*" -o -name "s3transfer*" -o -name "urllib3*" \) -exec rm -rf {} +')
    run(c, 'find .aws-sam/build/ -type f -name "six.py" -exec rm -f {} +')


@task
def deploy(c, params=None):
    run(c, 'sam package --s3-bucket stwind --s3-prefix forest --template-file .aws-sam/build/template.yaml --output-template-file .aws-sam/build/packaged.yml')
    run(c, 'sam deploy --template-file .aws-sam/build/packaged.yml --stack-name TheForest --capabilities CAPABILITY_IAM --parameter-overrides {}'.format(params))
