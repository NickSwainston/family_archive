# Web Application Installation


The following are instructions on how to setup up your nimbus instance for the first time. If you have already done this you can skip to :ref:`start_server`.

## Opening the Nimbus Instance Firewall

Once you've set up the instance you need to open the firewall.
Then make a costum tcp rule for ports 80 and 443, should look like this


Then follow this guide to check things step by step

https://uwsgi-docs.readthedocs.io/en/latest/tutorials/Django_and_nginx.html

The following is examples of how I got it to work.

## Goal 1: IP as URL

First try and get it to work with the nimbus IP as the URL. From directory containing manage.py run the command:

```bash
uwsgi --socket gleam_webapp.sock --module gleam_webapp.wsgi --chmod-socket=666
```

and nginx should look like this

```nginx
upstream django {
   server unix:///home/ubuntu/GleamXGPMonitoring/gleam_webapp/gleam_webapp.sock;
}

server {
   listen      80;
   server_name 146.118.70.58;
   charset     utf-8;

   client_max_body_size 75M;

   location /static {
      alias /home/ubuntu/GleamXGPMonitoring/gleam_webapp/static;
   }

   location / {
      uwsgi_pass  django;
      include     /home/ubuntu/GleamXGPMonitoring/gleam_webapp/uwsgi_params;
   }
}
```

and make sure the IP is in allowed hosts in settings.py:

```python
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '146.118.70.58']
```

Check if the works by using the IP as a URL in your browser.

## Static files errors

If it's not finding the static files then setup the setting.py like this

```python
STATIC_URL = '/static/'
STATICFILES_DIRS = (
   os.path.join(BASE_DIR, "static/"),
)
STATIC_ROOT = os.path.join(BASE_DIR, "static_host/")
```

then run

```bash
python manage.py collectstatic
```

and update the nginx to

```nginx
location /static {
   alias /home/ubuntu/GleamXGPMonitoring/gleam_webapp/static_host;
}
```

## Try a simple domain

Grab a free subdomain from https://www.duckdns.org/domains that points to your ip then update the url in nginx's severname, and ALLOWED_HOSTS in settings.py

## Getting a ssl certificate

Here are instructions on generating a ssl certificate

https://certbot.eff.org/instructions?ws=nginx&os=ubuntufocal