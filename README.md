# vps-setup
Setup instructions for my VPS

1. Log into your VPS provider and connect through SSH.
2. Install `docker` and `docker-compose` with `apt`
3. Create a new folder (e.g. `/hosting`)
4. Put the the `docker-compose.yml` file there, as well as a `.env` file with:
   - `HOSTNAME`: base URL for domain (e.g. dennishilhorst.nl)
   - `BASICAUTH`: basicauth setup for traefik. The value should be of the form
     `<username>:<hashed pw>`, where `<hashed pw>` is a password that is hashed with either MD5, SHA1 or [BCrypt](https://bcrypt-generator.com/)
   - `PGADMIN_DEFAULT_EMAIL`: email address for pgadmin login
   - `PGADMIN_DEFAULT_PASSWORD`: password for pgadmin login
5. Add DNS records to your domain:
   - an A record (and/or an AAAA record) pointing the `traefik` subdomain to the VPS.
   - an A record (and/or an AAAA record) pointing the `pgadmin` subdomain to the VPS.
   - an A record (and/or an AAAA record) pointing the `portainer` subdomain to the VPS.
6. Run `docker-compose up -d` to start your containers, and check that the connection works!

### Firewall setup
First setup a firewall in your VPS hosting provider, allowing only SSH and HTTP(S) requests (at ports 22, unless changed, 80 and 443). 
We use `ufw` to setup a firewall from within our VPS, following [this article on digitalocean](https://www.digitalocean.com/community/tutorials/how-to-set-up-a-firewall-with-ufw-on-ubuntu-20-04).
The steps are as follows:
1. Change default incoming/outgoing request policies:
   ```
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   ```
2. Allow incoming SSH connections:
   ```
   sudo ufw allow ssh
   ```
   or change `ssh` by `22` (default) or whatever SSH port you connect through SSH with.
3. Allow incoming HTTP(S) connections:
   ```
   sudo ufw allow http
   sudo ufw allow https
   ```
4. Enable extra rules as you'd like (enable or disable incoming requests from ports, perhaps filtered by IP).
5. Start the `ufw` firewall with
   ```
   sudo ufw enable
   ```
   which may disrupt existing SSH connections.
6. Check your setup with `ufw status verbose` to see if your firewall is setup correctly:
   ```
   Status: active
   Logging: on (low)
   Default: deny (incoming), allow (outgoing), deny (routed)
   New profiles: skip
   
   To                         Action      From
   --                         ------      ----
   22/tcp                     ALLOW IN    Anywhere
   22                         ALLOW IN    Anywhere
   80/tcp                     ALLOW IN    Anywhere
   443                        ALLOW IN    Anywhere
   22/tcp (v6)                ALLOW IN    Anywhere (v6)
   22 (v6)                    ALLOW IN    Anywhere (v6)
   80/tcp (v6)                ALLOW IN    Anywhere (v6)
   443 (v6)                   ALLOW IN    Anywhere (v6)
   ```

### To add services on subdomains:
Simply add an A record pointing to your VPS with the corresponding subdomain, and add the following labels in your project's `docker-compose.yaml`, at the webapp's service:
```
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.chef-web.rule=Host(`chef.dennishilhorst.nl`)"
  - "traefik.http.routers.chef-web.entrypoints=websecure"
  - "traefik.http.routers.chef-web.tls.certresolver=myresolver"
  - "traefik.http.services.chef-web.loadbalancer.server.port=5000"
```
replacing your subdomain. Make sure your app is listening at port 5000. Simply create a new stack on portainer, linking to the corresponding git repo.

In order to connect your postgres db to the pgadmin network in the main setup (the network is called `pgadmin-net` in the `docker-compose.yml`, simply use the following in your postgres service:
```
services:
  db:
    image: postgres
    ...
    hostname: my-hostname
    networks:
      - pgadmin-net
      - local-net
  web:
    ...
    networks:
      - local-net
volumes:
  dbdata:
networks:
  pgadmin-net:
    external: true
  local-net:

```
This makes sure the `db` service connects to the `pgadmin-net` external network, as well as an internal network `local-net`, to connect to the corresponding services. You can now login to the database of the `db` service from the pgadmin service using the hostname `my-hostname` and the username and password that you set!

## Debugging

It seemed like `snap` was using a lot (a LOT) of memory sometimes, also taking up all the available vCPUs I had for `kswap0` making and reading swap files, so I uninstalled it. However, I had to shut down my VPS while portainer was pulling and redeploying a stack. It failed to delete the old stack, making me unable to do this action again for this stack. Apparently, the stacks have indices, and they are in folders inside the portainer container image. I figured out how to solve it using [this reddit post](https://www.reddit.com/r/portainer/comments/11qawqq/getting_error_target_path_already_exists_when/) combined with [this stackoverflow post](https://stackoverflow.com/questions/34803466/how-to-list-the-content-of-a-named-volume-in-docker-1-9). Basically, what happens is the following (from the reddit post):
It seems that for some reason the previous "pull and redeploy" didn't complete, at least the last step, "remove the old folder". Then, when you try to rerun it, it cannot create the "old folder" because it already exists.

If you want to be able to rerun "pull and redeploy" again, what you need to do is remove this "old folder".
You need to go to `{PORTAINER_PATH}/data/compose`, there, you will see different folders that are named with "numbers". Every one of them corresponds with a stack of your portainer. If you see any of them that is named `[NUMBER]-old`, it is the "old folder" I was talking about. The only thing you need to do is remove it (You can rename it if you want to be sure you don't break anything) and try to "pull and redeploy" again. The process should work now

Now to find `PORTAINER_PATH`, run `docker volume list`, and find the volume with portainer's data. Then run `docker volume inspect <portainer_data>` (replacing `portainer_data` with the appropriate name). Go to the folder and remove any `...-old` directories. 

