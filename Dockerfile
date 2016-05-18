FROM  alpine:edge
RUN   apk -U add python py-pip git \
        && pip install dork-compose
ENTRYPOINT ["dork-compose"]
