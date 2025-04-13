#require File.expand_path('../sinatra.rb', __FILE__)

use Faye::RackAdapter, :mount => '/faye', :timeout => 25