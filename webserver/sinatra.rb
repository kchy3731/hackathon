DB = Sequel.connect("postgres://timeframe_webserver:1234@localhost/banan")

$appname = "Time/Frame"

get "/" do
  #redirect to('/home') if cookies.key? :auth

  erb :newuser
end