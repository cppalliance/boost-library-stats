
## Server installation

```
apt-get update
apt-get install postgresql nginx htop nload locate net-tools \
   phppgadmin python3-psycopg2 build-essential libpq-dev python3-venv
```

/etc/nginx/sites-available/boost-library-stats:
```
server {
    if ($host = boost-library-stats.cpp.al) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    listen 80;
    server_name boost-library-stats.cpp.al;
    error_log /var/log/nginx/error-boost-library-stats.log;
    access_log /var/log/nginx/access-boost-library-stats.log;
    location '/.well-known/acme-challenge' {
        default_type "text/plain";
        root /var/www/letsencrypt;
    }
    location / {
        return 301 https://boost-library-stats.cpp.al:8443/phppgadmin$request_uri;
    }

}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name boost-library-stats.cpp.al;
    error_log /var/log/nginx/error-boost-library-stats.log;
    access_log /var/log/nginx/access-boost-library-stats.log;
    include snippets/snakeoil.conf;
    # ssl_certificate /etc/letsencrypt/live/boost-library-stats.cpp.al/fullchain.pem; # managed by Certbot
    # ssl_certificate_key /etc/letsencrypt/live/boost-library-stats.cpp.al/privkey.pem; # managed by Certbot

    location '/.well-known/acme-challenge' {
        default_type "text/plain";
        root /var/www/letsencrypt;
    }
    location / {
        return 301 https://boost-library-stats.cpp.al:8443/phppgadmin$request_uri;
    }

}
```

Next,

```
ln -s /etc/nginx/sites-available/boost-library-stats /etc/nginx/sites-enabled/boost-library-stats
snap install certbot
certbot certonly # option 4
```

After the cert has been provisioned, adjust the nginx vhost to use the cert instead of the snippet shown above.  

```
systemctl restart nginx
```

In /etc/apache2/ports.conf change the ports to 8080 and 8443
open firewall ports 8080 8443
In apache's default-ssl.conf add:
```
        SSLCertificateFile    /etc/letsencrypt/live/boost-library-stats.cpp.al/fullchain.pem
        SSLCertificateKeyFile /etc/letsencrypt/live/boost-library-stats.cpp.al/privkey.pem
```

```
a2enmod ssl
ln -s /etc/apache2/sites-available/default-ssl.conf /etc/apache2/sites-enabled/default-ssl.conf
```

Remove " Require local" from /etc/apache2/conf-available/phppgadmin.conf 

```
systemctl restart apache2
```

```
su - postgres
psql
```

```
CREATE USER stats;
CREATE DATABASE stats OWNER stats;
ALTER ROLE stats
WITH PASSWORD '___';
ALTER ROLE postgres
WITH PASSWORD '___';
CREATE USER viewer
WITH PASSWORD 'stats345!';
\c stats
GRANT SELECT ON ALL TABLES IN SCHEMA public TO viewer;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
   GRANT SELECT ON TABLES TO viewer;
```

```
adduser stats
su - stats
cd /home/stats
python3 -m venv venv
git clone https://github.com/cppalliance/boost-library-stats
cd boost-library-stats
pip3 install -r requirements.txt
```

vi ~/.web-env-vars

```
export DATABASE_USER=stats
export DATABASE_PASSWORD=__
export DATABASE_NAME=stats
export DATABASE_HOST=127.0.0.1
export DATABASE_PORT=5432
export SECRET_KEY=__
export DJANGO_SETTINGS_MODULE='boost_library_stats.settings'
export RESTMOTE_USER=__
export RESTMOTE_PASSWORD=__
# export AWS_ACCESS_KEY_ID=
# export AWS_SECRET_ACCESS_KEY=
# export EMAIL_HOST=
# export EMAIL_HOST_USER=
# export EMAIL_HOST_PASSWORD=
```
The above values are on the machine.

```
. ~/.web-env-vars
./manage.py migrate
```

If available, copy over a db backup.

```
~/tmp$ scp ubuntu@boost-library-stats.cpp.al:/tmp/stats.boost-library-stats.2025-03-26-15-07-05.dump .
~/tmp$ scp stats.boost-library-stats.2025-03-26-15-07-05.dump ubuntu@boost-library-stats2.cpp.al:/tmp/
```

```
pg_restore -d stats stats.boost-library-stats.2025-03-26-15-07-05.dump
```

stats user crontab:

```
0 5 1 * * && . $HOME/venv/bin/activate && . $HOME/.web-env-vars && cd $HOME/boost-library-stats && $HOME/venv/bin/python3 ./scripts/collect_stats.py > /tmp/boost-library-stats.output 2>&1
```

