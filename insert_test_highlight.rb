require 'sequel'

# Connect to the database
DB = Sequel.connect("postgres://timeframe_webserver:1234@localhost/banan")

# Insert a test highlight
DB[:highlight].insert(
  timestamp: Time.now,
  headline: "AI-Generated Test Headline: Major Technology Breakthrough Announced",
  body: "Researchers have announced a significant breakthrough in quantum computing technology that could revolutionize data processing capabilities. The new approach combines traditional silicon-based hardware with novel quantum algorithms, potentially solving complex problems in minutes that would take conventional computers years to process. Industry experts are calling this development a potential game-changer for fields ranging from medicine to climate science.",
  user: 'wdbros@gmail.com'
)

puts "Test highlight inserted successfully!"
