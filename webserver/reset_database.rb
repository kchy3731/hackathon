require 'sequel'

DB = Sequel.connect("postgres://timeframe_webserver:1234@localhost/banan")

DB.drop_table? :source
DB.drop_table? :regular_feed
DB.drop_table? :highlight
DB.drop_table? :user

DB.create_table :user do
  String :id, primary_key: true # user's email
  timestamp :last_login
end

DB.create_table :highlight do
  primary_key :id
  timestamp :timestamp
  String :headline
  String :body
  foreign_key :user, :user, type: String
end

DB.create_table :regular_feed do
  primary_key :id
  timestamp :timestamp
  String :headline
  String :link
  foreign_key :highlight, :highlight
  foreign_key :user, :user, type: String
end

DB.create_table :source do
  primary_key :id
  String :type
  String :source
  foreign_key :user, :user, type: String
end

users = DB[:user]
sources = DB[:source]

users.insert('wdbros@gmail.com')
sources.insert(type: 'TWITTER', source: 'https://twitter.com/lilmonix3', user: 'wdbros@gmail.com')