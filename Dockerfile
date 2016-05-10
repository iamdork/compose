FROM  alpine:edge
RUN   apk -U add python py-pip git
ADD   requirements.txt /requirements.txt
RUN   pip install -r /requirements.txt
ADD   ./compose /compose
ADD   __main__.py /__main__.py
ENTRYPOINT python /code/__main__.py