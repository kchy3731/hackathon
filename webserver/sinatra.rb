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
  @sources = DB[:source].where(user: 'wdbros@gmail.com').all
  erb :settings
end

get "/add" do
  erb :add
end

post "/add" do
  feed_url = params[:feed_url]

  # Basic validation
  if feed_url.nil? || feed_url.empty?
    @error = "Please enter a valid RSS feed URL"
    return erb :add
  end

  # Check if the feed already exists for this user
  existing = DB[:source].where(source: feed_url, user: 'wdbros@gmail.com').first
  if existing
    @error = "This RSS feed is already in your sources"
    return erb :add
  end

  # Add to database
  begin
    DB[:source].insert(
      type: 'RSS',
      source: feed_url,
      user: 'wdbros@gmail.com'
    )
    redirect to('/settings')
  rescue => e
    @error = "Error adding feed: #{e.message}"
    erb :add
  end
end

get "/logout" do
  cookies.delete :auth if cookies.key? :auth

  redirect to('/')
end