require "faye"
require "sinatra"
require "sinatra/cookies"
require "sequel"

require_relative "faye.rb"
require_relative "sinatra.rb"

run Sinatra::Application
