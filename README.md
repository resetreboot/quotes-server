Quotes Service
==============

This is a simple quote service website to register the hilarious things said
at your office and then vote them to see which is the most funny.

What does it use
----------------

It has a backend written in Python with Bottle, a frontend with very simple 
jQuery javascript and it's all thought for being dockerized.

How to deploy on your system
----------------------------

* Get Docker.
* Clone this repo.
* Adjust the settings in the code (i.e. app.js's server line, Dockerfile paths)
* Go to the directory containing the repo's directory.
* Run: `docker build --rm -f quotes-server/docker/Dockerfile -t quotes:latest quotes-server/`
* Run  `docker run -d --name quotes -v [PATH_TO_STORE_THE_DB]:/var/quotes -p 6000:6000 -p 80:80 quotes:latest`

If all goes correctly, you should be able to see the site working at http://localhost.

Needs doing
-----------

* In fact, it's easy to vote a lot by the same user.
