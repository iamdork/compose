FROM  alpine:edge
RUN   apk -U add python py-pip git
ADD . /source
RUN pip install -e /source
ENTRYPOINT ["dork-compose"]
