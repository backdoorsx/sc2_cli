#!/usr/bin/env python3

import sys
import os

try:
    import random
    import string
    import json
    import requests
    import hashlib
    from passlib.hash import md5_crypt # md5_crypt in code
    import urllib.request
    from xml.etree import ElementTree
except ModuleNotFoundError:
    print('\n [-] CHeck modules!\n')
    input('Press any key to continue without requred modules.\n Use: pip3 install requests hashlib passlib')

TOKEN = "9ajdu4xyn1ig8nxsodr3"      # access token
#TOKEN = "th2tdy0no8v1zoh1fs59"      # access token

VERSION = '13'
KODI_CLI_FILE = 'kodi_cli.conf'     # config file shadowed
KODI_CLI_FILE2 = 'kodi_cli_db.json' # db save wathed movies/episodes + save wb link :-D :-D
VIDEO_PLAYER = 'vlc'
LABEL_LANG = 'sk'

class Sc2API:
    def query_search(search_name, tag_type):

        searched = []

        print(tag_type)
        if tag_type == 'new':
            QUERY_URL_API = "https://plugin.sc2.zone/api/media/filter/v2/news?type=movie&sort=dateAdded&order=desc&days=365&access_token={}".format(TOKEN)
        elif tag_type == 'movie' or tag_type == 'tvshow':
            QUERY_URL_API = "https://plugin.sc2.zone/api/media/filter/v2/search?sort=score&limit=20&type={}&order=desc&value={}&access_token={}".format(tag_type, search_name, TOKEN)
        else:
            QUERY_URL_API = "https://plugin.sc2.zone" + tag_type # NEXT/PREV PAGE, defaultne API vracia 100

        print(QUERY_URL_API)
        query_data = requests.get(QUERY_URL_API).json()

        next_page = None
        prev_page = None
        if tag_type == 'new' or tag_type == 'new_next_prev':
            if 'pagination' in list(query_data.keys()):
                next_prev_page = query_data['pagination']
                if 'next' in list(next_prev_page.keys()):
                    next_page = query_data['pagination']['next']
                    print(next_page)

                if 'prev' in list(next_prev_page.keys()):
                    prev_page = query_data['pagination']['prev']
                    print(prev_page)
                    
        data = query_data["hits"]
        data = data["hits"]
        
        for n in range(len(data)):

            d = data[n]
            s = d["_source"]
            i = s["info_labels"] # API shity, niekedy chyba v json "originaltitle"
            i2 = s['i18n_info_labels']
            
            if 'year' in list(i.keys()):
                get_year = i["year"]
            else:
                get_year = 'NaN'
                
            try:
                if len(i2) != 0:
                    info_label_dict = {}
                    for iil in i2:
                        if 'title' in list(iil.keys()):
                            if iil['title'] != '' and iil['title'] != None:
                                info_label_dict[iil['lang']]=iil['title']

                    if LABEL_LANG in list(info_label_dict.keys()):
                        searched.append((n, info_label_dict[LABEL_LANG], get_year, d["_id"]))     
                    elif len(list(info_label_dict.keys())) > 0:
                        searched.append((n, info_label_dict[list(info_label_dict.keys())[0]], get_year, d["_id"])) 

                            
            except ValueError:#KeyError:
                searched.append((n, 'NaN', get_year, d["_id"]))                         # nema nazov
                        
        return searched, next_page, prev_page


    def query_streams(idx):

        QUERY_URL_API = "http://plugin.sc2.zone/api/media/{}/streams?access_token={}".format(idx, TOKEN)
        query_data = requests.get(QUERY_URL_API).json()

        movie_data = []
        for data in query_data:

            try:
                movie_data.append((data['ident'],data['size'],data['video'],data['audio']))
            except KeyError:
                print('[-] Key Error!')

        return movie_data


    def query_search_season(idx):

        QUERY_URL_API = "https://plugin.sc2.zone/api/media/filter/v2/parent?value={}&sort=episode&access_token={}".format(idx, TOKEN)
        print(QUERY_URL_API)
        query_data = requests.get(QUERY_URL_API).json()

        data = query_data["hits"]
        data = data["hits"]    

        serial_data = []
        for n in range(len(data)):

            d = data[n]
            s = d["_source"]
            i = s["info_labels"]

            serial_data.append((d['_id'], i['mediatype'], i['season']))
            # ak najde v info_labels > mediatype episode namiesto season tak serial nema serie
            if i['mediatype'] == 'episode':
                i['mediatype']
                return 'episode'

        return serial_data


    def query_search_episode(idx):

        QUERY_URL_API = "https://plugin.sc2.zone/api/media/filter/v2/parent?value={}&sort=episode&access_token={}".format(idx, TOKEN)
        query_data = requests.get(QUERY_URL_API).json()

        data = query_data["hits"]
        data = data["hits"]

        episode_data = []
        for n in range(len(data)):

            d = data[n]
            s = d["_source"]
            i = s["info_labels"]

            if 'available_streams' in list(s.keys()):
                a = 1
            else:
                a = 0
            episode_data.append((d['_id'], i['mediatype'], i['episode'], a))

        return episode_data


class WebshareAPI:
    def __init__(self):
        self._base_url = "https://webshare.cz/api/"
        self._token = ""


    def login(self, user_name, password):

        salt = self.get_salt(user_name)
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        url = self._base_url + 'login/'
        password, digest = self.hash_password(user_name, password, salt)
        data = {
                'username_or_email' : user_name,
                'password' : password,
                'digest' : digest,
                'keep_logged_in' : 1
                }
        response = requests.post(url, data=data, headers=headers)
        assert(response.status_code == 200)
        root = ElementTree.fromstring(response.content)
        assert root.find('status').text == 'OK', 'Return code was not OK, debug info: status: {}, code: {}, message: {}'.format(
                    root.find('status').text,
                    root.find('code').text,
                    root.find('message').text)

        self._token = root.find('token').text
        status_login = root.find('status').text
        
        return status_login


    def hash_password(self, user_name, password, salt):
        
        password = hashlib.sha1(md5_crypt.hash(password, salt=salt).encode('utf-8')).hexdigest()
        digest = hashlib.md5((user_name + ':Webshare:' + password).encode('utf-8')).hexdigest()
        return password, digest


    def get_salt(self, user_name):
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        url = self._base_url + 'salt/'
        data = {'username_or_email' : user_name}
        response = requests.post(url, data=data, headers=headers)
        assert(response.status_code == 200)
        root = ElementTree.fromstring(response.content)
        assert root.find('status').text == 'OK', 'Return code was not OK, debug info: status: {}, code: {}, message: {}'.format(
                    root.find('status').text, 
                    root.find('code').text, 
                    root.find('message').text)

        return root.find('salt').text


    def get_download_link(self, ws_ident):
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        url = self._base_url + 'file_link/'
        data = {'ident' : ws_ident, 'wst' : self._token}
        response = requests.post(url, data=data, headers=headers)
        
        root = ElementTree.fromstring(response.content)

        
        if root.find('status').text == 'OK':
            return root.find('link').text
        else:
            return None


class Core:

    def cls():
        if os.name == 'nt':
            os.system('cls')
        else:
            os.system('clear')


    def menu():

        print('')
        print('   0) Settings')
        print('')
        print('   1) Find movies')
        print('   2) New releases movies')
        print('   3) Find series')
        print('')
        print('  99) Exit to KODI CLI stream cinema2')
        print('')

        
    def name(ver):

        r = random.randint(0,3)
        
        print('') 
        print('')

        if r == 0:                                                         
            print('     _/    _/    _/_/    _/_/_/    _/_/_/        _/_/_/  _/        _/_/_/')  
            print('    _/  _/    _/    _/  _/    _/    _/        _/        _/          _/   ')  
            print('   _/_/      _/    _/  _/    _/    _/        _/        _/          _/    ') 
            print('  _/  _/    _/    _/  _/    _/    _/        _/        _/          _/     ') 
            print(' _/    _/    _/_/    _/_/_/    _/_/_/        _/_/_/  _/_/_/_/  _/_/_/    ') 
        elif r == 1:                                                                                                                                    
            print(' ╦╔═╔═╗╔╦╗╦  ╔═╗╦  ╦')
            print(' ╠╩╗║ ║ ║║║  ║  ║  ║')
            print(' ╩ ╩╚═╝═╩╝╩  ╚═╝╩═╝╩')
        elif r == 2:
            print(' █  █▀ ████▄ ██▄   ▄█     ▄█▄    █    ▄█')
            print(' █▄█   █   █ █  █  ██     █▀ ▀▄  █    ██')
            print(' █▀▄   █   █ █   █ ██     █   ▀  █    ██')
            print(' █  █  ▀████ █  █  ▐█     █▄  ▄▀ ███▄ ▐█')
            print('   █         ███▀   ▐     ▀███▀      ▀ ▐')
            print(' ▀                                      ')
        elif r == 3:
            print(' ██╗  ██╗ ██████╗ ██████╗ ██╗     ██████╗██╗     ██╗')
            print(' ██║ ██╔╝██╔═══██╗██╔══██╗██║    ██╔════╝██║     ██║')
            print(' █████╔╝ ██║   ██║██║  ██║██║    ██║     ██║     ██║')
            print(' ██╔═██╗ ██║   ██║██║  ██║██║    ██║     ██║     ██║')
            print(' ██║  ██╗╚██████╔╝██████╔╝██║    ╚██████╗███████╗██║')
            print(' ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝     ╚═════╝╚══════╝╚═╝')

        print('  STREAM CINEMA v2')
        print(f'  Ver. 0x{VERSION} dedicated\n')
        print('  Support players [mpv, vlc, mplayer, cvlc] (Windows only VLC)')
        print('')


    def show_bytes(byte):
        
        B = float(byte)
        KB = float(1024)
        MB = float(KB ** 2) # 1,048,576
        GB = float(KB ** 3) # 1,073,741,824
        TB = float(KB ** 4) # 1,099,511,627,776
    
        if MB <= B < GB:
            return '{0:.2f} MB'.format(B/MB)
        else:
            return '{0:.2f} GB'.format(B/GB)


    def show_quality(video_width, video_height):
        
        if video_width == 1024:
            resolution = 'XGA '
        elif video_width == 1280:
            resolution = ' HD '
        elif video_width == 1920:
            resolution = 'FHD '
        elif video_width == 2048:
            resolution = ' 2K '
        elif video_width == 3840:
            resolution = 'UDH '
        elif video_width == 4096:
            resolution = ' 4K '
        else:
            resolution = 'NONE'

        return resolution
        
        
    def find_movie(tag):

        print('')
        print('  99) Back to Main menu')
        print('')

        all_data = []
        
        if tag == 'movie':
            name = input(' Find movie > ')                          # INPUT
        else:
            name = None                                             # INPUT
        
        if name == '99':
            return 99, 99
        else:

            db = Core.read_db()
            db_nameM = []
            for j in range(len(db)):
                db_nameM.append(db[j]['name'])

                              
            datax, nextP, prevP = Sc2API.query_search(name, tag)    # find movie by name
            for i in range(len(datax)):
                nameM = str(datax[i][1]) +'-'+ str(datax[i][2])
                if nameM in db_nameM:
                    seen = 's'
                else:
                    seen = ' '

                print("+"+76*"-")
                if i >= 10:
                    print("|  {}  |{}|  {}  |  {}".format(datax[i][0], seen, datax[i][1], datax[i][2]))
                else:
                    print("|  {}   |{}|  {}  |  {}".format(datax[i][0], seen,  datax[i][1], datax[i][2]))

            print("+"+76*"-"+"\n")
            print('')
            print('  back) Back to Find menu')
            print('')

            choose = input(' Choose number: ')                                  # INPUT
            
            if choose.isnumeric():
                choose = int(choose)
                if choose < len(datax):
                    print(datax[choose])
                    idx = datax[choose][3]                                      # get _id
                    nameOfMovie = datax[choose][1] +'-'+ str(datax[choose][2])  # get name
                    print('[+] Loading...')
                    all_data = Sc2API.query_streams(idx)                        # return all data choosed movie

                    return nameOfMovie, all_data
                else: 
                    return None, None
            elif choose == 'b' or choose == 'back':
                return None, None


    def find_serial():
        
        while True:

            print('')
            print('  99) Back to Main menu')
            print('')
            name = input(' Find series > ')                              # INPUT
            all_data = []

            if name == '99':
                return 99, 99, None, None
            elif len(name) > 0:
                datax, n1, n2 = Sc2API.query_search(name, 'tvshow')     # find movie by name

                for i in range(len(datax)):
                    print("+"+76*"-")
                    if i >= 10:
                        print("|  {}  |  {}  |  {}".format(datax[i][0], datax[i][1], datax[i][2]))
                    else:
                        print("|  {}   |  {}  |  {}".format(datax[i][0], datax[i][1], datax[i][2]))

                print("+"+76*"-"+"\n")
                print('')
                print('  99) Back to the Find series menu')
                print('')
            
                choose = input(' Choose number: ')                      # INPUT

                if choose.isnumeric():
                    choose = int(choose)

                    if choose == 99:
                        print('')
                        continue
                    elif choose < len(datax):
                        
                        print('\n[DEBUG] {}\n'.format(datax[choose]))

                        idx = datax[choose][-1]                         # get _id
                        nameOfMovie = datax[choose][-3]                 # get name

                        all_data = Sc2API.query_search_season(idx)      # return all data choosed movie

                        if all_data == 'episode':                       # serial nema serie
                            season = '0'
                        else:
                            for i in range(len(all_data)):
                                print("+"+76*"-")
                                print("|  {}  |  {}  |  {}".format(i, all_data[i][1], all_data[i][2]))

                            print("+"+76*"-"+"\n")
                            print('')
                            print('  99) Back to the Find series menu')
                            print('')
                
                            season = input('{} | Choose number > '.format(datax[choose][1])) # INPUT

                        if season.isnumeric():
                            season = int(season)
                            
                            if season == 99:
                                print('')
                                continue
                            else:
                                if all_data == 'episode':               # # serial nema serie
                                    all_data = [(0,0,1)]
                                else:
                                    print('\n[DEBUG] {}\n'.format(all_data[season]))
                                    idx = all_data[season][0]
                                    
                                e_data = Sc2API.query_search_episode(idx)


                                db = Core.read_db()
                                #print(db)
                                db_nameM = []
                                for j in range(len(db)):
                                    db_nameM.append(db[j]['name'])

                                #print(db_nameM)
                                # pridat - vytvorit pole kde budu vsetky episody
                                # ulozit zvolenu epizodu
                                # po skonceni bude moznost pokracovat v poli = play next episode
                                for i in range(len(e_data)):
                                    nameM = nameOfMovie + ' Season' + str(all_data[season][2]) + ' Episode' + str(i+1)

                                    if nameM in db_nameM:
                                        seen = 's'
                                    else:
                                        seen = ' '

                                    if int(e_data[i][3]) == 0:
                                        waiting = ' - WAITING FOR UPLOAD'
                                    else:
                                        waiting = ''

                                    print("+"+76*"-")
                                    if i < 10:
                                        print("|  {}   |{}|  {}  |  {} {}".format(i, seen, e_data[i][1], e_data[i][2], waiting))
                                    else:
                                        print("|  {}  |{}|  {}  |  {} {}".format(i, seen, e_data[i][1], e_data[i][2], waiting))


                                print("+"+76*"-"+"\n")
                                print('')
                                print('  99) Back to the Find series menu')
                                print('')
                                
                                episode = input('\n {} | Season{} | Choose number [{}-{}] > '.format(datax[choose][1], all_data[season][2],0 ,len(e_data)-1 )) # INPUT
                                    
                                if episode.isnumeric():
                                    episode = int(episode)
                                    
                                    if episode == 99:
                                        print('')
                                        continue
                                    elif episode >= len(e_data):
                                        input('[-] Episode {} is not available!'.format(episode+1))
                                    else:
                                        print('\n[DEBUG] {}\n'.format(e_data[episode]))
                                        nameOfMovie += ' Season{} Episode{}'.format(all_data[season][2], e_data[episode][2])
                                        idx = e_data[episode][0]
                                        all_data = Sc2API.query_streams(idx) # return all data choosed movie

                                        if len(all_data) > 0:
                                            return nameOfMovie, all_data, e_data, episode

                    else:
                        return None, None, None
        

    # treba opravic input
    def sort(movie_name, streams_data):
        streams_data = sorted(streams_data, key=lambda s: s[1], reverse=True)
        print('')
        for s in range(len(streams_data)):                          # ident size video audio
            stream_isva = streams_data[s]
            print("+"+76*"-")
            #print(stream_isva) datalog]
            video_width = stream_isva[2][0]['width']
            video_height = stream_isva[2][0]['height']
            quality = Core.show_quality(video_width, video_height)
            audio_data = ''
            size = int(stream_isva[1])
            size = Core.show_bytes(size)
            for audio in stream_isva[3]:
                audio_data += '['
                audio_data += audio['codec']
                audio_data += ' '
                audio_data += str(audio['channels']) + '.1'
                audio_data += ' '
                audio_data += audio['language']
                audio_data += ']'

            empty = str(len(streams_data))
            empty = len(empty) 
            empty = ' '*int(empty)

            if s < 10:
                space = ' '
            else:
                space = ''
                
            print("| {}{}   {}   {}".format(s, space, quality, size))
            print("| {}   {}   {}".format(empty, video_width, audio_data))

        print("+"+76*"-")
        print('')
        print('  99) Back to the Main menu')
        print('')
        
        while True:
            stream_choose = input(' {} > '.format(movie_name))      # INPUT

            if stream_choose.isnumeric():
                stream_choose = int(stream_choose)

                if stream_choose == 99:
                    return 0
                elif stream_choose < len(streams_data):
                    ident_stream = streams_data[stream_choose][0]   # get ident
                    Core.link(ident_stream, movie_name, streams_data[stream_choose])
                    return 0
            
        
    def link(ws_ident, movie_name, selected_streams_data):

        if os.path.exists(KODI_CLI_FILE):

            username, password = Core.get_hide()
            
            webshare = WebshareAPI()

            try:
                login = webshare.login(username, password)
            except:
                login = "FAIL"
                print('[-] Connection failed! Check webshare site or login for user {}'.format(username))

            if login == "OK":
                print("[+] Login success.")
                print("    Welcome {}".format(username))

                link = webshare.get_download_link(ws_ident)

                db = {
                    "name": movie_name,
                    "link": link,
                    "ws_id": selected_streams_data[0],
                    "id": selected_streams_data[1],
                    "info": selected_streams_data[2],
                    "info2": selected_streams_data[3]
                    }

                Core.add_db(db)

                Core.player(link)
            else:
                print("[-] Login failed.")
                link = None

        else:
            print('[-] For play set up video player and login in settings menu!')
            print('')


    def player(link):

        print("[+] Start playing...")
        print('')
        print(link)

        if os.name == 'nt':
            try:
                cmd = "start vlc -f --play-and-exit " + link
                os.system(cmd)
                print('The end!')
            except:
                print('[-] Dont run video player VLC player!. "Try test in cmd > start vlc" and check VLC player' )
                print('')
            
        else:
            try:
                if VIDEO_PLAYER == 'mpv':
                    print('[+] mpv:')
                    cmd = "mpv -fs --cache-secs=600 " + link
                elif VIDEO_PLAYER == 'vlc':
                    print('[+] vlc:')
                    cmd = "vlc --play-and-exit " + link
                elif VIDEO_PLAYER == 'mplayer':
                    print('[+] mplayer:')
                    cmd = "mplayer " + link
                elif VIDEO_PLAYER == 'cvlc':
                    print('[+] cvlc:')
                    cmd = "cvlc -f --play-and-exit " + link
                os.system(cmd)

                print('The end!')
            
            except:
                print('[-] Dont run video player {} player!'.format(VIDEO_PLAYER))
                print('')

    # db zatial json treba migrovat do sqlite ak bude velka
    def add_db(data):
        
        if not os.path.exists(KODI_CLI_FILE2):
            print('[-] Not found {}'.format(KODI_CLI_FILE2))
        else:
            with open(KODI_CLI_FILE2,'r') as f:
                print('.')
                file_data = json.load(f)
                print('..')

            file_data.append(data)
            file_data = json.dumps(file_data, indent = 4)
            
            with open(KODI_CLI_FILE2,'w') as f:
                f.write(file_data)
                print('....')


    def read_db():
        if not os.path.exists(KODI_CLI_FILE2):
            print('[-] Not found {}'.format(KODI_CLI_FILE2))
            return None
        else:
            with open(KODI_CLI_FILE2,'r') as f:
                file_data = json.load(f)

        return file_data
        

    def settings():
        print('')
        print(f'   1) Setting video player - {VIDEO_PLAYER}')
        print('   2) Setting webshare login')
        print(f'   3) Setting label language - {LABEL_LANG}')
        print('')
        print('  99) Back to the Main menu')
        print('')

        try:
            setting_menu = int(input(' settings > '))       # INPUT
            if type(setting_menu) == int:
                if setting_menu == 1:
                    #Core.set_player()                      # NOVA FUNKCIA ESTE NEEXISTUJE
                    print('[-] Sorry for this version is missing function set_player!')
                    print('[*] Default player is VLC')
                elif setting_menu == 2:
                    Core.set_login()
                elif setting_menu == 3:
                    #Core.set_label_lang()                      # NOVA FUNKCIA ESTE NEEXISTUJE
                    print('[-] Sorry for this version is missing function set_label_lang!')
                    print('[*] Default label language is SK')
                    
        except ValueError:
            Core.settings()
        

    def set_login():
        print('')
        print('  Login for webshare.cz. Set user name and password.')
        print('')
        print('  99) Back to the Main menu')
        print('')
        
        ws_username = ''
        ws_pass = ''
        
        try:
            login_input = input(' settings:login > webshare username: ')    # INPUT USER

            if len(login_input) != 0 and login_input != '99':
                ws_username = login_input

                login_input = input(' settings:login > webshare passwod: ') # INPUT PASS
                if len(login_input) != 0 and login_input != '99':
                    ws_pass = login_input

                    Core.hide(ws_username,ws_pass)
        except:
            pass


    def get_hide():
        
        u = ''
        p = ''
        with open(KODI_CLI_FILE) as f:
            hide_data = f.read()

        hide_data = hide_data[1024:]
        hide_data = hide_data.replace('\n', '')
        salt = hide_data[:8]
        salt_a = salt[:4]
        salt_b = salt[4:]

        len_u = []
        for ch in salt_a:
            if ch.isnumeric():
                len_u.append(ch)
        num = ''
        for ch in len_u:
            num += ch
        num = int(num)

        u = hide_data[8:]
        u = u[:num*2]

        len_p = []
        for ch in salt_b:
            if ch.isnumeric():
                len_p.append(ch)
        num = ''
        for ch in len_p:
            num += ch
        num = int(num)

        p = hide_data[8:]
        p = p[int(len(u)):]
        p = p[:num*2]

        ws_user = ''
        tag = 0
        for ch in u:
            if tag == 0:
                ws_user += ch
                tag = 1
            else:
                tag = 0
        
        ws_pass = ''
        tag = 0
        for ch in p:
            if tag == 0:
                ws_pass += ch
                tag = 1
            else:
                tag = 0

        return ws_user, ws_pass

    
    def hide(u,p):
        pool = string.ascii_letters + string.digits
        ascii_pool = string.ascii_letters
        gen = ''
        for ch in range(1024):
            gen += random.choice(pool)

        space_u = 4 - len(str(len(u)))
        space_p = 4 - len(str(len(p)))

        for i in range(space_u):
            gen += random.choice(ascii_pool)
        gen += str(len(u))

        for i in range(space_p):
            gen += random.choice(ascii_pool)
        gen += str(len(p))

        for ch in u:
            gen += ch + random.choice(pool)
            
        for ch in p:
            gen += ch + random.choice(pool)

        for ch in range(1024):
            gen += random.choice(pool)

        gen = gen[:-(8+(len(u)*2)+(len(p)*2))]

        print('[+] Shadowing login data...')
        print(len(gen))
        print(gen)

        try:
            f = open(KODI_CLI_FILE, 'w')
            f.write(gen)
            f.close()
            print('\n[+] Save shadow login data to {} OK\n'.format(KODI_CLI_FILE))
        except:
            print('\n[-] Failed save shadow login data to {} OK\n'.format(KODI_CLI_FILE))
        

if __name__ == "__main__":

    Core.cls()
    try:
        Core.name(10)
    except:
        pass

    if not os.path.exists(KODI_CLI_FILE2):
        with open(KODI_CLI_FILE2, 'w') as f:
            json.dump([], f, indent = 4)
                
    while True:
        Core.menu()
        
        menu = input(' sc2 > ')         # INPUT
        
        if menu.isnumeric():
            if menu == '0':
                Core.settings()
                
            elif menu == '1':
                while True:
                    movie_name, streams_data = Core.find_movie('movie')
                    
                    if movie_name == 99 and streams_data == 99:
                            break
                    elif movie_name != None or  streams_data != None:
                        Core.sort(movie_name, streams_data)
                    
            elif menu == '2':
                movie_name, streams_data = Core.find_movie('new')
                
                if movie_name == None and streams_data != None:
                    movie_name, streams_data = Core.find_movie(streams_data)
                elif movie_name != None or  streams_data != None:
                    Core.sort(movie_name, streams_data)
                    
            elif menu == '3':
                while True:
                    serial_name, streams_data, all_episode, e = Core.find_serial()
                    
                    if serial_name == 99 and streams_data == 99:
                        break
                    elif serial_name != None or streams_data != None:
                        Core.sort(serial_name, streams_data)

                    for n in range(e+1, len(all_episode)):
                        print('')
                        print(all_episode[n])
                        print(n)
                        if n >= 10:
                            serial_name = serial_name[:-2]
                        else:
                            serial_name = serial_name[:-1]
                        serial_name = serial_name + str(all_episode[n][2])
                        print('')
  
                        if int(all_episode[n][3]) == 0:
                            print('\n[-] Next episode is not available.\n')
                            break
                        
                        nxt = input('Next episode {} ? [Y/N] > '.format(all_episode[n][2]))
                        print(serial_name)
                        if nxt.upper() in ['', 'YES', 'Y', 'YOP', 'A', 'ANO']:
                            e_idx = all_episode[n][0]
                            _data = Sc2API.query_streams(e_idx)
                            Core.sort(serial_name, _data)
                        else:
                            break
                        
                        
            elif menu == '99':
                sys.exit(99)
        elif menu == 'vozitko':
            Core.player('../vozitko','cvlc')

    print('Exit')

    

