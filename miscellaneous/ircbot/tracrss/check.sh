#!/bin/bash


rmtag () {
	sed -e 's/<[^>]*>//g' -e 's/^[ \t]*//g' -e 's/[ \t]*$//g'
}

wget -q --user=ircbot --password=rahX5eir --no-check-certificate 'https://giccero.cloud.ik.bme.hu/trac/cloud/login?referer=%2Ftrac%2Fcloud%2Ftimeline%3Fmilestone%3Don%26ticket%3Don%26wiki%3Don%26max%3D50%26authors%3D%26daysback%3D1%26format%3Drss' -O-|grep -E '(<guid|<title|<link)' |
while read guid; read title; read link
do

	guid=$(rmtag <<<"$guid")
	title=$(rmtag <<<"$title")
	link=$(rmtag <<<"$link")
	
	if ! grep -qs "$guid" ~/tracrss/old
	then
		echo "$guid" >> ~/tracrss/old
		echo "$title <$link>" >~/irc/irc.atw.hu/#ik/in
	fi
done
