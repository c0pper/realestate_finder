# Docker
docker stop real-estate-finder && docker rm real-estate-finder && docker build --network=host -t real-estate-finder . && docker run -d --network=host --restart unless-stopped \
--env-file /home/pi/docker/bots/realestate_finder/.env \
--name real-estate-finder \
-v /home/pi/docker/bots/realestate_finder/listings:/app/listings \
-v /home/pi/docker/bots/realestate_finder/old_listings.txt:/app/old_listings.txt \
-v /home/pi/docker/bots/realestate_finder/ff_profile:/app/ff_profile \
--user $(id -u):$(id -g) \
real-estate-finder


docker stop real-estate-finder && docker rm real-estate-finder && docker build --network=host -t real-estate-finder . && docker run -d --network=host --restart unless-stopped \
--env-file .env \
--name real-estate-finder \
-v /home/simo/code/realestate_finder/listings/:/app/listings \
-v /home/simo/code/realestate_finder/old_listings.txt:/app/old_listings.txt \
-v /home/simo/.mozilla/firefox:/app/ff_profile \
real-estate-finder