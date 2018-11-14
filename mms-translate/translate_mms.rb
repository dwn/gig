require 'sinatra'
require 'twilio-ruby'
require 'unirest'
require 'sinatra/run-later'
require 'bing_translator'

mashape_key = ENV['MASHAPE_KEY']
bing_translate_id = ENV['BING_TRANSLATE_ID']
bing_translate_secret = ENV['BING_TRANSLATE_SECRET']
twilio_accountsid = ENV['TWILIO_ACCOUNT_SID']
twilio_authtoken = ENV['TWILIO_AUTH_TOKEN']
twilio_fromnumber = ENV['TWILIO_FROM_NUMBER']

def check_language(language)
  case language
  when /spanish/
    return "es"
  when /french/
    return "fr"
  when /german/
    return "de"
  when /italian/
    return "it"
  when /klingon/
    return "tlh"
  else
    return nil
  end
end

post '/translate' do
  @requested_language = params[:Body].strip
  @picture_url = params[:MediaUrl0]
  @incoming_number = params[:From]
puts @requested_language
puts @picture_url
puts @incoming_number

  # This block will execute after the /translate endpoint returns
  run_later do
    token_response = Unirest.post("https://camfind.p.mashape.com/image_requests",
      headers:{
        "X-Mashape-Key" => mashape_key
      },
      parameters:{
        "image_request[locale]" => "en_US",
        "image_request[remote_image_url]" => @picture_url
      })

    token = token_response.body['token']

puts "WAIT ******************************"
    # Need to wait for image analysis
    sleep(60)
puts "PROCEEDING ************************"

puts "GETTING MASHAPE RESPONSE..."
    # Get the details from the analysis
    image_response = Unirest.get "https://camfind.p.mashape.com/image_responses/#{token}",
    headers:{"X-Mashape-Key" => mashape_key}

    status = image_response.body['status']
    description = image_response.body['name']

puts "RESPONSE STATUS:"
puts status
puts "DESCRIPTION:"
puts description
puts "TRANSLATOR..."
    translator = BingTranslator.new(bing_translate_secret)
puts "TRANSLATING..."
    translated = translator.translate description, :from => 'en', :to => @language_format

puts "body: Got it, I think your picture contains: #{description}. In #{@requested_language} that would be: #{translated}"

puts "TWILIO..."
    @client = Twilio::REST::Client.new(twilio_accountsid, twilio_authtoken)
puts "SENDING SMS TO " + @incoming_number + " FROM " + twilio_fromnumber + "..."
    @client.messages.create(
      from: twilio_fromnumber,
      body: "Got it, I think your picture contains: #{description}. In #{@requested_language} that would be: #{translated}",
      to: @incoming_number
      )
puts message.sid
puts "FINISHED PROCESSING"
  end

  if @requested_language.nil? || @requested_language.empty?
    # Default to French
    @requested_language = "French"
  end

  if @requested_language.downcase == "list"
puts @requested_language + "<="
    # Return the allowed language list...
    twiml = Twilio::Response.new("","") do |r|
      r.Message "Supported languages for translation are: Spanish, French, German, Italian, and Klingon. Please send one of these with a picture and I'll translate it for you! Default language is French if one is not specified."
    end
puts "err0"
    return twiml.body
  end

  if @picture_url.nil? || @picture_url.empty?
puts @requested_language + "<=="
    twiml = Twilio::Response.new("","") do |r|
      r.Message "No image sent. Please send a picture with text indicating a supported translation language."
    end
puts "err1"
    return twiml.body
  end

  # Check language
  @language_format = check_language(@requested_language.downcase)

  if @language_format.nil?
puts @requested_language + "<==="
    twiml = Twilio::Response.new("","") do |r|
      r.Message "#{@requested_language} is not a supported translator language. Supported languages for translation are: Spanish, French, German, Italian, and Klingon. Please send one of these along with a picture and I'll translate it for you!"
    end
puts "err2"
    return twiml.body
  end

  content_type "text/xml"

  # Provide a quick response before processing the image with Camfind.
  twiml = Twilio::Response.new("","") do |r|
    r.Message "Analyzing your image...then I'll translate it. This may take a few..."
  end
puts "suc0"
  twiml.body
end
