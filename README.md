haikugrams
==========

_searching for those rarest of birds_
## install
```
git clone https://github.com/abelsonlive/haikugrams.git
```
## dependencies
```
git clone https://github.com/tumblr/pytumblr.git
cd pytumblr
sudo python setup.py install 
```
```
git clone https://github.com/tweepy/tweepy.git
cd tweepy
sudo python setup.py install 
```
```
sudo pip install nltk
```
```
python
>>> import nltk
>>> nltk.download()
>>> # select "cmudict" and "stopwords"
```
## config:
`haikugrams_tumblr.yml`:
```
blog: <your_tumblr_account_name>
consumer_key: xxxxxxxxxxxxxxxxxxxxxx
consumer_secret: xxxxxxxxxxxxxxxxxxxxxx
oauth_token: xxxxxxxxxxxxxxxxxxxxxx
oauth_token_secret: xxxxxxxxxxxxxxxxxxxxxx
```
`haikugrams_twitter.yml`:
```
consumer_key: xxxxxxxxxxxxxxxxxxxxxx
consumer_secret: xxxxxxxxxxxxxxxxxxxxxx
access_token: xxxxxxxxxxxxxxxxxxxxxx
access_token_secret: xxxxxxxxxxxxxxxxxxxxxx
```
## crontab
```
0,15,30,45 * * * * python <path_to_haikugrams_dir>/haikugrams.py 
```

## [tumblr](http://haikugrams.tumblr.com/)
## [twitter](http://twitter.com/haikugrams)

