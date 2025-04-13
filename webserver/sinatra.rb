DB = Sequel.connect("postgres://timeframe_webserver:1234@localhost/banan")

$appname = "Time/Frame"
$counter = 0

get "/" do
  redirect to('/home') if cookies.key? :auth

  erb :newuser
end

get "/circumvent" do
  cookies[:auth] = "banan"

  redirect to('/home')
end

get "/home" do
  redirect to('/') unless cookies.key? :auth

  erb :home
end

get "/settings" do
  erb :settings
end

get "/logout" do
  cookies.delete :auth if cookies.key? :auth

  redirect to('/')
end