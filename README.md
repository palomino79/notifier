# Notifier - a Scheduled Notification App
## About
Notifier is a scheduled notification app (also called a "reminder" app). 

How it works is very simple: you run the application, supplying a schedule in the form of a yaml file, which it parses and then, at the appropriate time, sends a push notification to a service and topic you specify.

## Usage
Notifier is meant to be ran as a docker compose application, although it can be ran as a simple python executable, as well.

It has a few mandatory environment variables that must be supplied at startup, and a few optional ones.

### docker compose (recommended)

```
---
services:
  notify:
    image: ghcr.io/palomino79/notifier:latest
    container_name: notifier
    restart: on-failure
    volumes:
      - ./schedule/schedule.yml:/schedule.yml # required
    environment:
      SCHEDULE_PATH: "/schedule.yml" # required - tells notifier where to look inside the container for its schedule
      PUSH_SERVICE_URL: "http://your.notification.url" # required
      TOPIC: "your-topic" # required
      # TEST_ON_START: True # optional - Defaults to False. Sends a notification to the PUSH_SERVICE_URL/TOPIC on successful application start.
      # SUPPRESS_SSL_WARNINGS: False # optional - Defaults to True
      # TIMEZONE: America/New_York # optional - Defaults to US/Eastern
```

### python script (not recommended)
```
export SCHEDULE_PATH="/path/to/schedule.yml"
export PUSH_SERVICE_URL="http://your.notification.url"
export TOPIC="your-topic"
python app.py
```

### Example schedule.yaml file
```
birthdays:
  John_Doe:
    description: John's birthday
    date: July 4
    notify_before_days: 2
    notify_time: 12:00 PM
    push_url: http://my.push.url
    push_topic: birthday-alerts
  Jane_Doe:
    description: Jane's birthday
    date: January 1
    notify_before_days: 2
    notify_time: 12:00 PM
    push_url: http://my.push.url
    push_topic: birthday-alerts

holidays:
  Mothers_Day:
    description: Mother's Day
    date:
        month: May
        weekday: Sunday
        day_n: 2
    notify_before_days: 2
    notify_time: 12:00 PM
```

The structure is relatively simple: You must have a top level heading (such as `birthdays`), followed by a subheading (such as `John_Doe`), followed by the parameters of the date you want to specify. Any other date structure will raise an internal exception in the application.

For these, you will receive a message for each on the days leading up to, and including the day of, the described event at the given notification time, in the style of
```
"Upcoming reminder: {description}. When: {date of event}"
```

This is to say that, for John Doe's birthday, you would receive a notification starting on July 2nd, and on each subsequent day up to and including July 4th, at 12:00 PM each day.

Additionally, in this example John Doe's birthday has a push url and topic override. The service will use these values over the containerwide environment variables for `PUSH_SERVICE_URL` and `TOPIC`. 

For Mother's Day, which is called a "floating holiday," we have special logic that allows a user to describe when the day should occur. Mother's Day in the United States is the second Sunday in May, and so we describe its date with

```
date:
  month: May
  weekday: Sunday
  day_n: 2
```

And since `Mothers_Day` does not have a `push_url` or `push_topic` override, it will use the environental defaults for those values that you set for your container or local environment. 

## Contributing
Contributions are welcome, and this would be a great project for someone new to python to get started, as it has very few requirements and a relatively simple architecture.

Currently there is no formal code of conduct, but contributors should behave sensibly and in keeping with the typical code of conduct found in other open source projects. Just be nice and treat people with a sense of inclusivity. 

If you find a bug or have an idea for an inprovement, or want to open a PR, please open a ticket first, describe the issue as concisely and clearly as possible, and then open a Pull Request with your changes. 

This project currently has no truly stringent development guidelines, but we do ask that users squash commits on their branches before opening a Pull Request.
