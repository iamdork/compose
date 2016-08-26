FROM nginx

LABEL dork.root="/usr/share/nginx" \
      dork.dependencies="html;test"

RUN echo "This is created during build." >> /usr/share/nginx/html/test.txt
RUN mkdir /usr/share/nginx/test
RUN echo "This is also created during build." >> /usr/share/nginx/test/test.txt
