FROM  alpine:edge
RUN   apk -U add python py-pip git
ADD   requirements.txt /requirements.txt
RUN   pip install -r /requirements.txt
ADD   ./dork /dork
ADD   __main__.py /__main__.py
COPY  docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
