from nltk.corpus import cmudict
import nltk
import tweepy
import pytumblr
import re, time, string, random, json, yaml
from collections import defaultdict

# initialize carnegie mellon dictionary
d = cmudict.dict()

def number_of_syllables(word):
    return [len(list(y for y in x if y[-1].isdigit())) for x in d[word]]

def remove_duplicates(input):
    output = []
    for x in input:
        if x not in output:
            output.append(x)
    return output

def detect_potential_haiku(tweet):
    tweet = tweet.encode('utf-8')

    # ignore tweets with @s, RT's and MT's and numbers
    if re.search(r'@|#|MT|RT|[0-9]+', tweet):
        return None

    tweet = re.sub("&", "and", tweet)

    # remove punctuation
    tweet = tweet.translate(string.maketrans("",""), string.punctuation)

    # strip and lower text
    tweet = tweet.strip()
    tweet = tweet.lower()

    # split tweet into a list of words
    words = tweet.split()

    # detect suitable tweets, annotate words with each words' number of syllables
    n_syllables = []
    clean_words = []

    for word in words:
        try:
            n_syllable = number_of_syllables(word)[0]
        except KeyError:
            return None
        if n_syllable > 5:
            return None
        else:
            n_syllables.append(n_syllable)
            clean_words.append(word.strip().lower())

    # remove tweekus that are really long
    clean_tweet = ' '.join(clean_words)
    if len(clean_tweet) > 125:
        return None
    # make sure tweets have the proper number of syllables
    total_syllables = sum(n_syllables)
    if total_syllables == 17:
        return {"words" : clean_words, "syllables" : n_syllables }
    else:
        return None

def is_proper_haiku(haiku_dict):
    words = haiku_dict['words']
    syllables = haiku_dict['syllables']

    # make sure lines break at 5 and 12
    syllable_cum_sum = []
    syllables_so_far = 0
    for syllable in syllables:
        syllables_so_far = syllables_so_far + syllable
        syllable_cum_sum.append(syllables_so_far)
    if 5 in syllable_cum_sum and 12 in syllable_cum_sum:
        return True
    else:
        return False

def format_haiku(haiku_dict):
    words = haiku_dict['words']
    syllables = haiku_dict['syllables']
    syllable_count = 0
    haiku = ''
    for i, word in enumerate(words):
        if syllable_count == 5:
            haiku = haiku + " / "
        if syllable_count == 12:
            haiku = haiku + " / "
        syllable_count = syllable_count + syllables[i]
        haiku += word.strip() + " "
    return haiku.strip()

def detect_haikus(tweets):
    if len(tweets)==0:
        return []
    print "\tdetecting haikus..."
    haikus = []
    status_ids_so_far = []
    for tweet in tweets:
        h = detect_potential_haiku(tweet.text)
        if h is not None:
            if is_proper_haiku(h):
                if tweet.id_str not in status_ids_so_far:
                    print "HAIKU: ", format_haiku(h)
                    haiku = {
                        "haiku_text": format_haiku(h),
                        "status_id": tweet.id_str,
                        "user": tweet.user.screen_name
                    }

                    status_ids_so_far.append(tweet.id_str)
                    haikus.append(haiku)

    print "\tfound %d haikus..." % len(haikus)
    return haikus

def extract_chars(h):
    chars = [char.lower() for char in h if char!=" " and char!="/" and char!=""]
    return "".join(sorted(chars)).strip()

def detect_haikugrams(haikus):
    text_to_test = [extract_chars(h['haiku_text']) for h in haikus]
    dups = defaultdict(list)
    for i,t in enumerate(text_to_test):
        dups[t].append(haikus[i])

    dupkus = [d for d in dups.values() if len(d)>1]

    haikugrams = [dd for d in dupkus for dd in d if len(set([ddd['haiku_text'] for ddd in d]))>1]
    return haikugrams

def connect_to_twitter(conf="haikugrams_twitter.yml"):
    c = yaml.safe_load(open(conf).read())

    # # authenticate
    auth = tweepy.OAuthHandler(c['consumer_key'], c['consumer_secret'])
    auth.set_access_token(c['access_token'], c['access_token_secret'])
    return tweepy.API(auth)

def fetch_new_tweets(api):
    print "\tscraping twitter feed..."
    words = nltk.corpus.stopwords.words('english')
    tweets = []
    for page in range(1, 180):
        word = random.choice(words)
        try:
            print "\tsearching for %s..." % word
            tweet_list = api.search(q=word, lang="en")
        except tweepy.error.TweepError as e:
            print e
        else:
            tweets.extend(tweet_list)
    return tweets

def post_tweets(api, haikus, hg=False):
    for h in haikus:
        if hg:
            print "\tposting HG tweet!"
        else:
            print "\tposting tweet!"
        haiku = h['haiku_text']
        url = "http://www.twitter.com/%s/status/%s" % ( h['user'], h['status_id'] )
        if hg:
            haiku = "HG: "+ haiku
        try:
            api.update_status(haiku + " - " + url)
        except tweepy.TweepError:
            continue

def connect_to_tumblr(conf='haikugrams_tumblr.yml'):
    c = yaml.safe_load(open(conf).read())
    return pytumblr.TumblrRestClient(c['consumer_key'], c['consumer_secret'], c['oauth_token'], c['oauth_token_secret'])

def format_tumble(haiku):
    haiku_text = re.sub(" / ", " <br></br> ", haiku['haiku_text'])
    url = "http://twitter.com/%s/status/%s" % (haiku['user'], haiku['status_id'])
    embdded_tweet = '''<p> <a href=%s target="_blank"> %s</a> </p>
                       <br></br>
                       <blockquote class="twitter-tweet"><p> <a href="%s"> original tweet </a></blockquote>
                       <script async src="//platform.twitter.com/widgets.js" charset="utf-8"></script>''' % (url, haiku_text, url)
    return {
        'body': embdded_tweet,
        'url': url
    }

def post_tumbles(api, haikus, conf='haikugrams_tumblr.yml'):
    c = yaml.safe_load(open(conf).read())
    for h in haikus:
        tumbleku = format_tumble(h)
        try:
            print "\tposting tumble!"
            api.create_text(c['blog'], body=tumbleku['body'], format="html")
        except Exception as e:
            print e
        time.sleep(2)

def main(twt_api, tmbl_api):

    # open up and read in our haiku database
    lines = open('haikus.json', "r").read().split("\n")
    haikus = []
    for line in lines:
        if line != "" and line !=" ":
            try:
                haikus.append(json.loads(line))
            except:
                continue
    print "\tread in %d haikus" % len(haikus)
    

    lines = open('haikugrams.json', "r").read().split("\n")
    haikugrams = []
    for line in lines:
        if line != "" and line !=" ":
            try:
                haikugrams.append(json.loads(line))
            except:
                continue
    print "\tread in %d haikugrams" % len(haikugrams)
    # open up and read in our haikugrams databse:

    # find some tweets
    tweets = fetch_new_tweets(api=twt_api)
    new_haikus = detect_haikus(tweets)

    # if we find a haiku, append it to our current haiku database
    if len(new_haikus)>0:
        f = open('haikus.json', "a")
        for h in new_haikus:
            f.write(json.dumps(h)+"\n")
        f.close()
        haikus += new_haikus

        post_tumbles(api=tmbl_api, haikus=new_haikus)
        post_tweets(api=twt_api, haikus=new_haikus)


    # find haikugrams
    hgs = detect_haikugrams(haikus)
    current_hg_ids = [h['status_id'] for h in haikugrams]
    new_hgs = [h for h in hgs if h['status_id'] not in current_hg_ids]

    if len(new_hgs ) > 1:
        f = open('haikugrams.json', "a")
        for h in new_hgs:
            f.write(json.dumps(h)+"\n")
        f.close()

        # alert that we have found a haikugram!
        post_tweets(api=twt_api, haikus=new_hgs , hg=True)

    else:
        print "no haikugrams"

if __name__ == '__main__':
    twt_api = connect_to_twitter()
    tmbl_api = connect_to_tumblr()

    main(twt_api, tmbl_api)
