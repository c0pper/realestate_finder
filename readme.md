# Docker
docker stop real-estate-finder && docker rm real-estate-finder && docker build --network=host -t real-estate-finder . && docker run -d --network=host --restart unless-stopped \
-v /home/pi/docker/bots/realestate_finder/listings:/app/listings \
-v /home/pi/docker/bots/realestate_finder/old_listings.txt:/app/old_listings.txt \
-v /home/pi/docker/bots/realestate_finder/ff_profile:/app/ff_profile
--env-file /home/pi/docker/bots/realestate_finder/.env \
--name real-estate-finder real-estate-finder