FROM debian:jessie-backports

#   This file is part of Quotes Server.
#
#   Quotes Server is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   Quotes Server is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with Quotes Server.  If not, see <http://www.gnu.org/licenses/>.

MAINTAINER Jose Carlos Cuevas reset.reboot@gmail.com
WORKDIR /
# Install dependencies
RUN apt-get update
RUN apt-get install -y build-essential libffi-dev python3 python3-pip nginx
# Configure locales
ENV LC_ALL "en_US.UTF-8"
# Install the frontend
COPY src/html/ /quotes-frontend/
# Configure NGINX
COPY docker/frontend.conf /etc/nginx/sites-enabled/default
# Install requirements
COPY requirements.txt /quotes-server/
RUN pip3 install -r /quotes-server/requirements.txt
# Setup the application
COPY src/*.py /quotes-server/
COPY src/config.ini /quotes-server/
COPY docker/entrypoint.sh /quotes-server
RUN mkdir /var/quotes
WORKDIR /quotes-server
ENTRYPOINT ["/bin/bash", "entrypoint.sh"] 
EXPOSE 6000
EXPOSE 8888
EXPOSE 80
VOLUME /var/quotes
