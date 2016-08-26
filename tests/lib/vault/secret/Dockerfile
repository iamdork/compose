FROM nginx

ARG VAULT_VERSION="0.6.1"
ARG VAULT_TOKEN=''
ARG VAULT_ADDR='http://172.17.0.1'

RUN apt-get update && apt-get install wget unzip -y

RUN wget https://releases.hashicorp.com/vault/${VAULT_VERSION}/vault_${VAULT_VERSION}_linux_amd64.zip \
 && unzip -d /bin vault_${VAULT_VERSION}_linux_amd64.zip

ONBUILD ARG VAULT_TOKEN=''
ONBUILD ARG VAULT_ADDR='http://172.17.0.1'

ONBUILD RUN echo "$(vault read -field=value secret/SECRET_A) $(vault read -field=value secret/SECRET_B)" > /usr/share/nginx/html/index.html
