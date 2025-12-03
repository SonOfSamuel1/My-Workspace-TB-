/**
 * Calendar Tool
 * Manage calendar and scheduling through email agent
 */

const logger = require('../logger');
const { google } = require('googleapis');
const fs = require('fs').promises;
const path = require('path');

class CalendarTool {
  constructor() {
    this.name = 'calendar';
    this.description = 'Calendar management and scheduling';
    this.calendar = null;
    this.auth = null;
    this.initialized = false;
  }

  /**
   * Initialize Google Calendar API
   */
  async initialize() {
    if (this.initialized) return;

    try {
      // Load credentials from environment or file
      const credentialsPath = process.env.GOOGLE_CREDENTIALS_PATH ||
                            path.join(process.env.HOME, '.gmail-mcp', 'gcp-oauth.keys.json');

      const tokenPath = process.env.GOOGLE_TOKEN_PATH ||
                       path.join(process.env.HOME, '.gmail-mcp', 'credentials.json');

      // Check if files exist
      try {
        await fs.access(credentialsPath);
        await fs.access(tokenPath);
      } catch (error) {
        logger.warn('Google Calendar credentials not found, using mock mode', {
          credentialsPath,
          tokenPath
        });
        this.initialized = true;
        return;
      }

      // Load credentials
      const credentials = JSON.parse(await fs.readFile(credentialsPath, 'utf-8'));
      const token = JSON.parse(await fs.readFile(tokenPath, 'utf-8'));

      // Create OAuth2 client
      const { client_id, client_secret } = credentials.installed || credentials.web;
      this.auth = new google.auth.OAuth2(client_id, client_secret, 'urn:ietf:wg:oauth:2.0:oob');
      this.auth.setCredentials(token);

      // Initialize calendar API
      this.calendar = google.calendar({ version: 'v3', auth: this.auth });

      this.initialized = true;
      logger.info('Google Calendar API initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Google Calendar API', {
        error: error.message
      });
      this.initialized = true; // Set to true to prevent repeated attempts
    }
  }

  /**
   * Execute calendar action
   */
  async execute(parameters) {
    const { action, ...params } = parameters;

    logger.info('Executing calendar action', { action, params });

    // Initialize if not already done
    await this.initialize();

    switch (action) {
      case 'create_event':
        return await this.createEvent(params);
      case 'check_availability':
        return await this.checkAvailability(params);
      case 'list_events':
        return await this.listEvents(params);
      case 'cancel_event':
        return await this.cancelEvent(params);
      case 'update_event':
        return await this.updateEvent(params);
      case 'find_time':
        return await this.findAvailableTime(params);
      default:
        throw new Error(`Unknown calendar action: ${action}`);
    }
  }

  /**
   * Create calendar event
   */
  async createEvent(params) {
    const {
      title,
      start,
      end,
      attendees = [],
      description = '',
      location = '',
      reminders = { useDefault: true }
    } = params;

    logger.info('Creating calendar event', { title });

    // If no calendar API, return mock response
    if (!this.calendar) {
      return {
        success: true,
        eventId: `mock_event_${Date.now()}`,
        title,
        start,
        end,
        attendees,
        url: `https://calendar.google.com/event/mock`,
        summary: `Event "${title}" created successfully (mock mode)`
      };
    }

    try {
      // Format attendees
      const formattedAttendees = attendees.map(email => ({ email }));

      // Create event
      const event = {
        summary: title,
        description,
        location,
        start: {
          dateTime: new Date(start).toISOString(),
          timeZone: process.env.TIMEZONE || 'America/New_York'
        },
        end: {
          dateTime: new Date(end).toISOString(),
          timeZone: process.env.TIMEZONE || 'America/New_York'
        },
        attendees: formattedAttendees,
        reminders
      };

      const response = await this.calendar.events.insert({
        calendarId: 'primary',
        resource: event,
        sendNotifications: true
      });

      return {
        success: true,
        eventId: response.data.id,
        title: response.data.summary,
        start: response.data.start.dateTime,
        end: response.data.end.dateTime,
        attendees: response.data.attendees || [],
        url: response.data.htmlLink,
        summary: `Event "${title}" created successfully`
      };
    } catch (error) {
      logger.error('Failed to create calendar event', {
        error: error.message
      });
      throw new Error(`Failed to create event: ${error.message}`);
    }
  }

  /**
   * Check availability
   */
  async checkAvailability(params) {
    const { start, end, emails = [] } = params;

    logger.info('Checking availability', { start, end, emails });

    // If no calendar API, return mock response
    if (!this.calendar) {
      return {
        available: true,
        conflicts: [],
        suggestedTimes: [
          { start, end, available: true }
        ]
      };
    }

    try {
      // Query free/busy information
      const response = await this.calendar.freebusy.query({
        requestBody: {
          timeMin: new Date(start).toISOString(),
          timeMax: new Date(end).toISOString(),
          timeZone: process.env.TIMEZONE || 'America/New_York',
          items: [
            { id: 'primary' },
            ...emails.map(email => ({ id: email }))
          ]
        }
      });

      const busyTimes = response.data.calendars.primary.busy || [];
      const available = busyTimes.length === 0;

      // Find suggested times if not available
      const suggestedTimes = [];
      if (!available) {
        // Simple algorithm to find gaps between busy times
        const startTime = new Date(start).getTime();
        const endTime = new Date(end).getTime();
        const duration = endTime - startTime;

        // Check slots after each busy period
        for (const busy of busyTimes) {
          const busyEnd = new Date(busy.end).getTime();
          const potentialStart = busyEnd;
          const potentialEnd = potentialStart + duration;

          if (potentialEnd <= new Date(end).getTime() + 86400000) { // Within 24 hours
            suggestedTimes.push({
              start: new Date(potentialStart).toISOString(),
              end: new Date(potentialEnd).toISOString(),
              available: true
            });
          }
        }
      }

      return {
        available,
        conflicts: busyTimes,
        suggestedTimes: suggestedTimes.slice(0, 3) // Return top 3 suggestions
      };
    } catch (error) {
      logger.error('Failed to check availability', {
        error: error.message
      });
      throw new Error(`Failed to check availability: ${error.message}`);
    }
  }

  /**
   * List events
   */
  async listEvents(params) {
    const {
      startDate = new Date().toISOString(),
      endDate,
      maxResults = 10,
      query = ''
    } = params;

    logger.info('Listing calendar events', { startDate, endDate, maxResults });

    // If no calendar API, return mock response
    if (!this.calendar) {
      return {
        events: [],
        count: 0
      };
    }

    try {
      const queryParams = {
        calendarId: 'primary',
        timeMin: startDate,
        maxResults,
        singleEvents: true,
        orderBy: 'startTime'
      };

      if (endDate) {
        queryParams.timeMax = endDate;
      }

      if (query) {
        queryParams.q = query;
      }

      const response = await this.calendar.events.list(queryParams);

      const events = response.data.items || [];

      return {
        events: events.map(event => ({
          id: event.id,
          title: event.summary,
          start: event.start.dateTime || event.start.date,
          end: event.end.dateTime || event.end.date,
          location: event.location,
          attendees: (event.attendees || []).map(a => a.email),
          url: event.htmlLink,
          status: event.status
        })),
        count: events.length
      };
    } catch (error) {
      logger.error('Failed to list events', {
        error: error.message
      });
      throw new Error(`Failed to list events: ${error.message}`);
    }
  }

  /**
   * Cancel event
   */
  async cancelEvent(params) {
    const { eventId, sendNotifications = true } = params;

    logger.info('Canceling event', { eventId });

    // If no calendar API, return mock response
    if (!this.calendar) {
      return {
        success: true,
        eventId,
        summary: 'Event canceled successfully (mock mode)'
      };
    }

    try {
      await this.calendar.events.delete({
        calendarId: 'primary',
        eventId,
        sendNotifications
      });

      return {
        success: true,
        eventId,
        summary: 'Event canceled successfully'
      };
    } catch (error) {
      logger.error('Failed to cancel event', {
        error: error.message
      });
      throw new Error(`Failed to cancel event: ${error.message}`);
    }
  }

  /**
   * Update event
   */
  async updateEvent(params) {
    const { eventId, updates, sendNotifications = true } = params;

    logger.info('Updating event', { eventId, updates });

    // If no calendar API, return mock response
    if (!this.calendar) {
      return {
        success: true,
        eventId,
        summary: 'Event updated successfully (mock mode)'
      };
    }

    try {
      // First get the existing event
      const existing = await this.calendar.events.get({
        calendarId: 'primary',
        eventId
      });

      // Merge updates
      const updatedEvent = {
        ...existing.data,
        ...updates
      };

      // Handle date updates
      if (updates.start) {
        updatedEvent.start = {
          dateTime: new Date(updates.start).toISOString(),
          timeZone: process.env.TIMEZONE || 'America/New_York'
        };
      }
      if (updates.end) {
        updatedEvent.end = {
          dateTime: new Date(updates.end).toISOString(),
          timeZone: process.env.TIMEZONE || 'America/New_York'
        };
      }

      const response = await this.calendar.events.update({
        calendarId: 'primary',
        eventId,
        resource: updatedEvent,
        sendNotifications
      });

      return {
        success: true,
        eventId: response.data.id,
        title: response.data.summary,
        url: response.data.htmlLink,
        summary: 'Event updated successfully'
      };
    } catch (error) {
      logger.error('Failed to update event', {
        error: error.message
      });
      throw new Error(`Failed to update event: ${error.message}`);
    }
  }

  /**
   * Find available time slots
   */
  async findAvailableTime(params) {
    const {
      duration = 60, // minutes
      earliestStart = new Date().toISOString(),
      latestEnd = new Date(Date.now() + 7 * 86400000).toISOString(), // 7 days
      preferredTimes = [],
      attendees = []
    } = params;

    logger.info('Finding available time slots', { duration, attendees });

    // If no calendar API, return mock response
    if (!this.calendar) {
      const mockStart = new Date(earliestStart);
      mockStart.setHours(10, 0, 0, 0);
      const mockEnd = new Date(mockStart.getTime() + duration * 60000);

      return {
        found: true,
        suggestions: [{
          start: mockStart.toISOString(),
          end: mockEnd.toISOString(),
          score: 1.0
        }]
      };
    }

    try {
      // Get busy times
      const response = await this.calendar.freebusy.query({
        requestBody: {
          timeMin: earliestStart,
          timeMax: latestEnd,
          timeZone: process.env.TIMEZONE || 'America/New_York',
          items: [
            { id: 'primary' },
            ...attendees.map(email => ({ id: email }))
          ]
        }
      });

      const busyTimes = response.data.calendars.primary.busy || [];

      // Find free slots
      const freeSlots = [];
      let currentTime = new Date(earliestStart).getTime();
      const endTime = new Date(latestEnd).getTime();
      const durationMs = duration * 60000;

      // Sort busy times
      busyTimes.sort((a, b) => new Date(a.start) - new Date(b.start));

      for (const busy of busyTimes) {
        const busyStart = new Date(busy.start).getTime();

        // Check if there's a gap before this busy time
        if (currentTime + durationMs <= busyStart) {
          freeSlots.push({
            start: new Date(currentTime).toISOString(),
            end: new Date(currentTime + durationMs).toISOString(),
            score: this.scoreTimeSlot(currentTime, preferredTimes)
          });
        }

        currentTime = Math.max(currentTime, new Date(busy.end).getTime());
      }

      // Check remaining time after last busy period
      if (currentTime + durationMs <= endTime) {
        freeSlots.push({
          start: new Date(currentTime).toISOString(),
          end: new Date(currentTime + durationMs).toISOString(),
          score: this.scoreTimeSlot(currentTime, preferredTimes)
        });
      }

      // Sort by score and return top suggestions
      freeSlots.sort((a, b) => b.score - a.score);

      return {
        found: freeSlots.length > 0,
        suggestions: freeSlots.slice(0, 5)
      };
    } catch (error) {
      logger.error('Failed to find available time', {
        error: error.message
      });
      throw new Error(`Failed to find available time: ${error.message}`);
    }
  }

  /**
   * Score a time slot based on preferences
   */
  scoreTimeSlot(timestamp, preferredTimes) {
    const date = new Date(timestamp);
    const hour = date.getHours();
    let score = 0.5; // Base score

    // Prefer business hours
    if (hour >= 9 && hour <= 17) {
      score += 0.3;
    }

    // Prefer mornings
    if (hour >= 9 && hour <= 12) {
      score += 0.2;
    }

    // Check against preferred times
    for (const preferred of preferredTimes) {
      const prefDate = new Date(preferred);
      if (Math.abs(timestamp - prefDate.getTime()) < 3600000) { // Within 1 hour
        score += 0.5;
      }
    }

    return Math.min(score, 1.0);
  }

  /**
   * Register with email agent
   */
  register(emailAgent) {
    emailAgent.registerTool(this.name, this);
    logger.info('Calendar tool registered with email agent');
  }
}

module.exports = new CalendarTool();
module.exports.CalendarTool = CalendarTool;
