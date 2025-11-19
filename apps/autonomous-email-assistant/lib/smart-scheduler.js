/**
 * Smart Scheduling System
 *
 * AI-powered meeting scheduling that finds optimal times
 * considering preferences, patterns, and constraints.
 */

const logger = require('./logger');

class SmartScheduler {
  constructor(config = {}) {
    this.config = {
      workingHours: config.workingHours || { start: 9, end: 17 },
      timezone: config.timezone || 'America/New_York',
      defaultMeetingLength: config.defaultMeetingLength || 30,
      bufferTime: config.bufferTime || 10,
      lunchTime: config.lunchTime || { start: 12, end: 13 },
      focusBlocks: config.focusBlocks || [],
      preferredTimes: config.preferredTimes || ['morning', 'late_afternoon'],
      avoidBackToBack: config.avoidBackToBack !== false,
      maxMeetingsPerDay: config.maxMeetingsPerDay || 6
    };
  }

  /**
   * Find optimal meeting times
   */
  async findOptimalTimes(options) {
    const {
      duration = this.config.defaultMeetingLength,
      attendees = [],
      withinDays = 7,
      minSlots = 3,
      meetingType = 'general',
      constraints = {}
    } = options;

    logger.info('Finding optimal meeting times', {
      duration,
      attendees: attendees.length,
      withinDays
    });

    // Get calendar events for all attendees
    const allBusySlots = await this.getallBusySlots(attendees, withinDays);

    // Generate all possible time slots
    const possibleSlots = this.generateTimeSlots(duration, withinDays);

    // Filter and score slots
    const availableSlots = [];

    for (const slot of possibleSlots) {
      if (this.isSlotAvailable(slot, allBusySlots)) {
        const score = this.scoreSlot(slot, {
          meetingType,
          constraints,
          attendees
        });

        availableSlots.push({
          start: slot.start,
          end: slot.end,
          score,
          reasons: this.explainScore(slot, score)
        });
      }
    }

    // Sort by score (highest first)
    availableSlots.sort((a, b) => b.score - a.score);

    // Return top N slots
    return availableSlots.slice(0, minSlots);
  }

  /**
   * Generate possible time slots
   */
  generateTimeSlots(duration, withinDays) {
    const slots = [];
    const now = new Date();

    for (let day = 0; day < withinDays; day++) {
      const date = new Date(now);
      date.setDate(date.getDate() + day);

      // Skip weekends
      if (date.getDay() === 0 || date.getDay() === 6) {
        continue;
      }

      // Generate slots for this day
      const daySlots = this.generateSlotsForDay(date, duration);
      slots.push(...daySlots);
    }

    return slots;
  }

  /**
   * Generate slots for a specific day
   */
  generateSlotsForDay(date, duration) {
    const slots = [];
    const { start, end } = this.config.workingHours;

    // Start from working hours start time
    let currentHour = start;
    let currentMinute = 0;

    while (currentHour < end) {
      const slotStart = new Date(date);
      slotStart.setHours(currentHour, currentMinute, 0, 0);

      const slotEnd = new Date(slotStart);
      slotEnd.setMinutes(slotEnd.getMinutes() + duration);

      // Check if slot ends before working hours end
      if (slotEnd.getHours() < end || (slotEnd.getHours() === end && slotEnd.getMinutes() === 0)) {
        slots.push({ start: slotStart, end: slotEnd });
      }

      // Move to next slot (15-minute increments)
      currentMinute += 15;
      if (currentMinute >= 60) {
        currentHour++;
        currentMinute = 0;
      }
    }

    return slots;
  }

  /**
   * Check if slot is available
   */
  isSlotAvailable(slot, busySlots) {
    // Check against busy slots
    for (const busy of busySlots) {
      if (this.slotsOverlap(slot, busy)) {
        return false;
      }
    }

    // Check lunch time
    const { lunchTime } = this.config;
    if (this.isInLunchTime(slot, lunchTime)) {
      return false;
    }

    // Check focus blocks
    for (const focusBlock of this.config.focusBlocks) {
      if (this.isInFocusBlock(slot, focusBlock)) {
        return false;
      }
    }

    return true;
  }

  /**
   * Check if two slots overlap
   */
  slotsOverlap(slot1, slot2) {
    return slot1.start < slot2.end && slot1.end > slot2.start;
  }

  /**
   * Check if slot is during lunch time
   */
  isInLunchTime(slot, lunchTime) {
    const startHour = slot.start.getHours();
    const endHour = slot.end.getHours();

    return (startHour >= lunchTime.start && startHour < lunchTime.end) ||
           (endHour > lunchTime.start && endHour <= lunchTime.end);
  }

  /**
   * Check if slot is in focus block
   */
  isInFocusBlock(slot, focusBlock) {
    const slotDay = slot.start.getDay();
    const slotHour = slot.start.getHours();

    if (focusBlock.days && !focusBlock.days.includes(slotDay)) {
      return false;
    }

    if (focusBlock.hours) {
      return slotHour >= focusBlock.hours.start && slotHour < focusBlock.hours.end;
    }

    return false;
  }

  /**
   * Score a time slot based on preferences
   */
  scoreSlot(slot, options) {
    let score = 100;
    const { meetingType, constraints } = options;

    // Time of day preference
    const hour = slot.start.getHours();
    const timePreference = this.getTimePreference(hour);
    score += timePreference;

    // Meeting type optimization
    if (meetingType === '1:1' && hour >= 14) {
      score += 10; // Prefer afternoon for 1:1s
    } else if (meetingType === 'team' && hour >= 9 && hour <= 11) {
      score += 10; // Prefer morning for team meetings
    } else if (meetingType === 'external' && hour >= 10 && hour <= 15) {
      score += 15; // Prefer mid-day for external meetings
    }

    // Day of week optimization
    const day = slot.start.getDay();
    if (day === 1) {
      score -= 5; // Slightly avoid Monday mornings
    } else if (day === 5) {
      score -= 5; // Slightly avoid Friday afternoons
    } else if (day === 2 || day === 3) {
      score += 5; // Prefer Tuesday/Wednesday
    }

    // Early in the week for important meetings
    if (constraints.important && (day === 2 || day === 3)) {
      score += 10;
    }

    // Time zone considerations
    if (constraints.timeZones && constraints.timeZones.length > 0) {
      const tzScore = this.scoreTimeZones(slot, constraints.timeZones);
      score += tzScore;
    }

    // Avoid back-to-back if configured
    if (this.config.avoidBackToBack) {
      // Would need calendar context to check this
      // For now, slight preference for times with buffer
      if (slot.start.getMinutes() === 0) {
        score += 3; // On the hour = easier to have buffer
      }
    }

    return score;
  }

  /**
   * Get time preference score
   */
  getTimePreference(hour) {
    const { preferredTimes } = this.config;
    let score = 0;

    for (const pref of preferredTimes) {
      if (pref === 'morning' && hour >= 9 && hour < 12) {
        score += 15;
      } else if (pref === 'afternoon' && hour >= 13 && hour < 15) {
        score += 10;
      } else if (pref === 'late_afternoon' && hour >= 15 && hour < 17) {
        score += 12;
      } else if (pref === 'early_morning' && hour >= 8 && hour < 9) {
        score += 8;
      }
    }

    // Penalize very early or very late
    if (hour < 9) score -= 5;
    if (hour >= 16) score -= 3;

    return score;
  }

  /**
   * Score time zones
   */
  scoreTimeZones(slot, timeZones) {
    // Convert slot time to all time zones
    let worstHour = null;

    for (const tz of timeZones) {
      const tzTime = this.convertToTimeZone(slot.start, tz);
      const tzHour = tzTime.getHours();

      // Check if reasonable time
      if (tzHour < 8 || tzHour > 18) {
        return -50; // Very bad time for someone
      }

      if (worstHour === null || tzHour < 9 || tzHour > 17) {
        worstHour = tzHour;
      }
    }

    // All time zones are reasonable
    if (worstHour >= 9 && worstHour <= 17) {
      return 20; // Great for all time zones
    } else {
      return 5; // Acceptable but not ideal
    }
  }

  /**
   * Convert time to time zone (simplified)
   */
  convertToTimeZone(date, timezone) {
    // In production, use moment-timezone or date-fns-tz
    // For now, simplified conversion
    const utc = date.getTime();
    const offsets = {
      'America/New_York': -5,
      'America/Chicago': -6,
      'America/Denver': -7,
      'America/Los_Angeles': -8,
      'Europe/London': 0,
      'Europe/Paris': 1,
      'Asia/Tokyo': 9
    };

    const offset = offsets[timezone] || 0;
    const converted = new Date(utc);
    converted.setHours(converted.getHours() + offset);

    return converted;
  }

  /**
   * Explain why a slot got its score
   */
  explainScore(slot, score) {
    const reasons = [];
    const hour = slot.start.getHours();
    const day = slot.start.getDay();

    // Time of day
    if (hour >= 9 && hour < 12) {
      reasons.push('Morning time (preferred)');
    } else if (hour >= 15 && hour < 17) {
      reasons.push('Late afternoon (preferred)');
    }

    // Day of week
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    if (day === 2 || day === 3) {
      reasons.push(`${days[day]} (optimal day)`);
    }

    // Score interpretation
    if (score >= 130) {
      reasons.push('Excellent time');
    } else if (score >= 110) {
      reasons.push('Good time');
    } else if (score >= 100) {
      reasons.push('Acceptable time');
    }

    return reasons;
  }

  /**
   * Get busy slots for attendees (mock - would integrate with calendar API)
   */
  async getAllBusySlots(attendees, withinDays) {
    // In production, this would call calendar API for each attendee
    // For now, return empty array (all times available)
    logger.debug('Getting busy slots', { attendees, withinDays });

    // Mock busy slots for testing
    const busySlots = [];

    // Example: Block out some times
    // busySlots.push({
    //   start: new Date('2025-11-08T14:00:00'),
    //   end: new Date('2025-11-08T15:00:00')
    // });

    return busySlots;
  }

  /**
   * Format time slot for display
   */
  formatSlot(slot) {
    const options = {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      timeZoneName: 'short'
    };

    return {
      display: slot.start.toLocaleString('en-US', options),
      start: slot.start.toISOString(),
      end: slot.end.toISOString(),
      score: slot.score,
      reasons: slot.reasons
    };
  }

  /**
   * Generate meeting invitation text
   */
  generateInvitationText(slots, options = {}) {
    const { recipientName, meetingPurpose, duration } = options;

    const formattedSlots = slots.map((slot, index) =>
      `${index + 1}. ${this.formatSlot(slot).display}`
    ).join('\n');

    return `Hi ${recipientName || '[Name]'},

Thank you for reaching out${meetingPurpose ? ` about ${meetingPurpose}` : ''}.

I'm available at the following times${duration ? ` for a ${duration}-minute meeting` : ''}:

${formattedSlots}

Please let me know which time works best, and I'll send a calendar invitation.

Best regards,
Executive Email Assistant`;
  }

  /**
   * Analyze calendar patterns
   */
  async analyzeCalendarPatterns(daysToAnalyze = 30) {
    logger.info('Analyzing calendar patterns', { daysToAnalyze });

    // In production, would analyze historical calendar data
    // Return patterns like:
    // - Busiest days of week
    // - Busiest times of day
    // - Average meetings per day
    // - Meeting duration patterns
    // - Free time patterns

    return {
      busiestDay: 'Tuesday',
      busiestTime: '2-4 PM',
      avgMeetingsPerDay: 4.2,
      avgMeetingDuration: 45,
      preferredMeetingTimes: ['10-11 AM', '3-4 PM'],
      leastBusyDay: 'Friday',
      recommendations: [
        'Consider blocking Friday afternoons for focused work',
        'Tuesday afternoons are very busy - limit new meetings',
        'Morning meetings (9-11 AM) have highest attendance'
      ]
    };
  }

  /**
   * Suggest reschedule times for a meeting
   */
  async suggestReschedule(originalMeeting, reason = 'conflict') {
    const duration = originalMeeting.duration || this.config.defaultMeetingLength;

    // Find times close to the original
    const originalDate = new Date(originalMeeting.start);
    const sameDaySlots = await this.findOptimalTimes({
      duration,
      withinDays: 1,
      constraints: { preferSameDay: true }
    });

    // Also suggest alternative days
    const altDaySlots = await this.findOptimalTimes({
      duration,
      withinDays: 7,
      minSlots: 2
    });

    return {
      reason,
      sameDay: sameDaySlots,
      alternativeDays: altDaySlots,
      message: this.generateRescheduleMessage(originalMeeting, sameDaySlots, altDaySlots)
    };
  }

  /**
   * Generate reschedule message
   */
  generateRescheduleMessage(original, sameDaySlots, altSlots) {
    let message = `I need to reschedule our meeting originally planned for ${original.start}.`;

    if (sameDaySlots.length > 0) {
      message += '\n\nWould any of these times on the same day work instead?\n';
      message += sameDaySlots.map((slot, i) =>
        `${i + 1}. ${this.formatSlot(slot).display}`
      ).join('\n');
    }

    message += '\n\nAlternatively, I'm also available:\n';
    message += altSlots.map((slot, i) =>
      `${i + 1}. ${this.formatSlot(slot).display}`
    ).join('\n');

    return message;
  }
}

module.exports = SmartScheduler;
