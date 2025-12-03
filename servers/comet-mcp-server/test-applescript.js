#!/usr/bin/env node

// Simple test to verify AppleScript execution works
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

async function testAppleScript() {
  console.log('Testing AppleScript execution...\n');

  // Test 1: Check if Comet is installed
  console.log('Test 1: Checking if Comet is in Applications...');
  try {
    const { stdout } = await execAsync('ls /Applications/ | grep -i comet');
    console.log('✅ Found:', stdout.trim());
  } catch (error) {
    console.log('❌ Comet not found in /Applications/');
    console.log('   Please ensure Comet browser is installed\n');
  }

  // Test 2: Check if Comet is running
  console.log('\nTest 2: Checking if Comet is running...');
  try {
    const { stdout } = await execAsync(`osascript -e 'tell application "System Events" to (name of processes) contains "Comet"'`);
    const isRunning = stdout.trim() === 'true';
    console.log(isRunning ? '✅ Comet is running' : '⚠️ Comet is not running');
  } catch (error) {
    console.log('❌ Error checking process:', error.message);
  }

  // Test 3: Test basic AppleScript execution
  console.log('\nTest 3: Testing basic AppleScript...');
  try {
    const { stdout } = await execAsync(`osascript -e 'return "Hello from AppleScript"'`);
    console.log('✅ AppleScript works:', stdout.trim());
  } catch (error) {
    console.log('❌ AppleScript failed:', error.message);
  }

  // Test 4: Check accessibility permissions hint
  console.log('\nTest 4: Accessibility Permissions Check');
  console.log('⚠️  Please ensure Terminal/VS Code has Accessibility permissions:');
  console.log('   System Preferences → Security & Privacy → Privacy → Accessibility');
  console.log('   Add and enable your terminal application\n');
}

testAppleScript().catch(console.error);