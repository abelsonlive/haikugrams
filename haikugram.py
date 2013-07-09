from nltk.corpus import cmudict
import nltk
import tweepy
import pytumblr
import re, time, string, random, json, yaml

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

def extract_chars(text):
    chars = [char.lower() for char in text if char is not " " and char is not "/"]
    return "".join(sorted(chars))

def is_anagram(tweet_one, tweet_two):
    chars_one = extract_chars(tweet_one)
    chars_two = extract_chars(tweet_two)
    if chars_one == chars_two:
        return True
    else:
        return False

def find_haikugrams(haikus):
    haikugrams = []
    for oh in haikus:
        for nh in haikus:
            # ignore statuses which are precisely the same
            if nh['status_id'] == oh['status_id'] or nh['haiku_text'] == oh['haiku_text']:
                continue

            # otherwise try to find haikugrams
            else:
                if is_anagram(oh['haiku_text'], nh['haiku_text']):
                    hg = {
                    'haiku_one': oh,
                    'haiku_two': nh
                    }
                    haiku_grams.append(hg)

    if len(haikugrams) == 0:
        return None
    else:
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

def connect_to_tumblr(conf='haikugrams_tumblr.yml'):
    c = yaml.safe_load(open(conf).read())
    return pytumblr.TumblrRestClient(c['consumer_key'], c['consumer_secret'], c['oauth_token'], c['oauth_token_secret'])

def format_tumble(haiku):
    haiku_text = re.sub(" / ", " <br></br> ", haiku['haiku_text'])
    url = "http://twitter.com/%s/status/%s" % (haiku['user'], haiku['status_id'])
    embdded_tweet = '''<p><a href=%s target="_blank"> %s</a> </p><br></br><blockquote class="twitter-tweet"><p> %s <a href="%s"> haiku </a></blockquote>
<script async src="//platform.twitter.com/widgets.js" charset="utf-8"></script>''' % (url, haiku_text, haiku_text, url)
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
    f = open('haikus.json', "r")
    haikus = []
    for line in f.readlines():
        if line != "" and line !=" ":
            haikus.append(json.loads(line))
    f.close()
    print "\tread in %d haikus" % len(haikus)
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

    # how many haikus do we have now?
    n_haikus = len(haikus)

    # try to find a haikugrams within our haiku set
    print "\ntrying to find a haikugram within %d haikus" % n_haikus
    haikugrams = find_haikugrams(haikus)

    if haikugrams is None:

        # alert that we havent found a haikugram
        print "\tno haikugrams yet..."

        # announce progres on twitter
        if n_haikus > 0:
            try:
                twt_api.update_status("i've found %d haikus so far, but no haikugrams yet" % n_haikus)
            except tweepy.error.TweepError as e:
                print e

    else:
        # alert that we have found a haikugram!
        print "\tfound a haikugram!!!!!!!!!"

        # append it to our list of haikugrams
        f = open('haikugrams.json', "a")
        for hg in haikugrams:
            f.write(json.dumps(hg)+"\n")
        f.close()

        api.update_status("I've found a haikugram!!!!!")
        time.sleep(5)
        api.update_status(haikugrams[0]['haiku_one']['haiku_text'])
        time.sleep(5)
        api.update_status(haikugrams[0]['haiku_two']['haiku_text'])

if __name__ == '__main__':
    twt_api = connect_to_twitter()
    tmbl_api = connect_to_tumblr()

    main(twt_api, tmbl_api)

