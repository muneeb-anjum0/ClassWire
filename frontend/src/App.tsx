import React, { useState, useEffect } from 'react';
import './App.css';
import { apiService } from './services/api';
import { TimetableData, ApiResponse, StatusData, ConfigData } from './types/api';
import TimetableTable from './components/TimetableTable/TimetableTable';
import SummaryStats from './components/SummaryStats/SummaryStats';
import StatusIndicator from './components/StatusIndicator/StatusIndicator';
import SemesterManager from './components/SemesterManager/SemesterManager';
import LoginScreen from './components/LoginScreen/LoginScreen';
import { AuthProvider, useAuth } from './context/AuthContext';

function AppContent() {
  const { user, isAuthenticated, logout, loading: authLoading } = useAuth();
  // Custom sign out confirmation dialog
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const handleLogoutClick = () => setShowLogoutConfirm(true);
  const handleLogoutConfirm = () => {
    setShowLogoutConfirm(false);
    logout();
  };
  const handleLogoutCancel = () => setShowLogoutConfirm(false);
  const [timetableData, setTimetableData] = useState<TimetableData | null>(null);
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isScraperRunning, setIsScraperRunning] = useState(false);
  const [isSemesterUpdateRunning, setIsSemesterUpdateRunning] = useState(false);
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error' | 'warning'>('idle');
  const [message, setMessage] = useState('');
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const [showSemesterManager, setShowSemesterManager] = useState(false);
  const [operationInProgress, setOperationInProgress] = useState(false);

  // Computed state
  const noSemestersConfigured = config && (!config.semester_filter || config.semester_filter.length === 0);

  // Helper function to filter timetable items based on configured semesters
  const getFilteredTimetableItems = () => {
    if (!timetableData?.items || !config?.semester_filter || config.semester_filter.length === 0) {
      return timetableData?.items || [];
    }

    const filteredItems = timetableData.items.filter(item => {
      if (!item.semester) return false;
      
      const itemSemester = item.semester.trim();
      
      return config.semester_filter.some(configSemester => {
        const configSemesterTrimmed = configSemester.trim();
        
        // Direct match
        if (itemSemester === configSemesterTrimmed) return true;
        
        // Enhanced flexible matching for different formats - handles ANY spacing variation
        const flexibleMatch = (item: string, config: string) => {
          // 1. Exact match
          if (item === config) return true;
          
          // 2. Basic normalization (consistent spacing)
          const normalizeBasic = (str: string) => {
            return str
              .replace(/\s+/g, ' ')  // Multiple spaces to single space
              .replace(/\s*\(\s*/g, '(')  // Remove spaces around opening parentheses
              .replace(/\s*\)\s*/g, ')')  // Remove spaces around closing parentheses
              .replace(/\s*-\s*/g, ' - ')  // Normalize dashes with consistent spacing
              .trim()
              .toLowerCase();
          };
          
          const itemNormalized = normalizeBasic(item);
          const configNormalized = normalizeBasic(config);
          
          if (itemNormalized === configNormalized) return true;
          
          // 3. Compact match (remove all spaces) - handles "BS(CS)-2C" vs "BS (CS) - 2 C"
          const itemCompact = item.replace(/\s+/g, '').toLowerCase();
          const configCompact = config.replace(/\s+/g, '').toLowerCase();
          
          if (itemCompact === configCompact) return true;
          
          // 4. Pattern-based matching for section variations
          const itemPattern = item.match(/^(.*?)\s*-\s*(\d+)\s*([A-Z]*)$/i);
          const configPattern = config.match(/^(.*?)\s*-\s*(\d+)\s*([A-Z]*)$/i);
          
          if (itemPattern && configPattern) {
            const itemProgram = itemPattern[1].replace(/\s+/g, '').toLowerCase();
            const itemNumber = itemPattern[2];
            const itemSection = itemPattern[3].toLowerCase();
            
            const configProgram = configPattern[1].replace(/\s+/g, '').toLowerCase();
            const configNumber = configPattern[2];
            const configSection = configPattern[3].toLowerCase();
            
            return (itemProgram === configProgram && 
                    itemNumber === configNumber && 
                    itemSection === configSection);
          }
          
          return false;
        };
        
        console.debug(`🔍 Comparing: "${itemSemester}" vs "${configSemesterTrimmed}"`);
        
        return flexibleMatch(itemSemester, configSemesterTrimmed);
      });
    });

    // Deduplicate items based on course code, semester, time, and room
    // This prevents duplicate entries for the same class
    const deduplicatedItems = filteredItems.filter((item, index, array) => {
      const currentKey = `${item.semester}-${item.course || item.course_code}-${item.time}-${item.room}`;
      return array.findIndex(otherItem => {
        const otherKey = `${otherItem.semester}-${otherItem.course || otherItem.course_code}-${otherItem.time}-${otherItem.room}`;
        return otherKey === currentKey;
      }) === index;
    });

    console.debug(`🎯 Filtered from ${timetableData.items.length} to ${filteredItems.length} items, deduplicated to ${deduplicatedItems.length} items`);
    
    return deduplicatedItems;
  };

  // Load initial data on component mount (must be called before early returns)
  useEffect(() => {
    if (isAuthenticated) {
      loadLatestTimetable();
      loadConfig();
      checkStatus();
    }
  }, [isAuthenticated]);

  // Check for no semesters configured and set warning message
  useEffect(() => {
    if (config && timetableData && noSemestersConfigured && !isScraperRunning && !operationInProgress) {
      setStatus('warning');
      setMessage('No semesters configured. Please add semesters to filter and organize your schedule.');
    }
  }, [config, timetableData, noSemestersConfigured, isScraperRunning, operationInProgress]);

  // Show loading screen while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Show login screen if not authenticated
  if (!isAuthenticated) {
    return <LoginScreen />;
  }

  const loadConfig = async () => {
    try {
      const response = await apiService.getConfig();
      console.log('Config response:', response); // Debug log
      if (response.success && response.data) {
        setConfig(response.data);
        console.log('Loaded config:', response.data); // Debug log
      } else {
        console.error('Failed to load config:', response);
      }
    } catch (error) {
      console.error('Error loading config:', error);
    }
  };

  const loadLatestTimetable = async (force = false) => {
    if (operationInProgress && !force) {
      console.log('Operation in progress, skipping timetable load');
      return;
    }
    
    try {
      setIsLoading(true);
      setOperationInProgress(true);
      const response = await apiService.getLatestTimetable();
      if (response.success && response.data) {
        setTimetableData(response.data);
        setStatus('success');
        setMessage(response.cached ? 'Loaded cached data' : 'Data loaded successfully');
      } else {
        setTimetableData(null);
        setStatus('warning');
        setMessage('No timetable data available. Try running a manual scrape.');
      }
    } catch (error) {
      console.error('Error loading timetable:', error);
      setTimetableData(null);
      setStatus('error');
      setMessage('Failed to load timetable data');
    } finally {
      setIsLoading(false);
      setOperationInProgress(false);
    }
  };

  const checkStatus = async () => {
    try {
      const response: ApiResponse<StatusData> = await apiService.getStatus();
      if (response.success && response.data) {
        setLastUpdate(response.data.last_update);
      }
    } catch (error) {
      console.error('Error checking status:', error);
    }
  };

  const runScraper = async () => {
    if (isScraperRunning || operationInProgress) {
      console.log('Scraper already running or operation in progress');
      return;
    }

    // Check if semesters are configured before running scraper
    if (!config?.semester_filter || config.semester_filter.length === 0) {
      setStatus('error');
      setMessage('No semesters configured. Please add semesters before running the scraper.');
      return;
    }
    
    try {
      setIsScraperRunning(true);
      setIsLoading(true);
      setOperationInProgress(true);
      setStatus('loading');
      setMessage('Running scraper...');
      
      const response = await apiService.runScraper();
      if (response.success && response.data) {
        setTimetableData(response.data);
        setStatus('success');
        setMessage(response.message || 'Scrape completed successfully');
        await checkStatus(); // Update last update time
      } else {
        setStatus('error');
        setMessage(response.error || 'Scrape failed');
        setTimetableData(null);
      }
    } catch (error) {
      console.error('Error running scraper:', error);
      setStatus('error');
      setMessage('Failed to run scraper');
      setTimetableData(null);
    } finally {
      setIsScraperRunning(false);
      setIsLoading(false);
      setOperationInProgress(false);
    }
  };

  // Special version of runScraper that bypasses semester validation (used for auto-run after updating semesters)
  const runScraperWithSemesters = async (semestersList: string[]) => {
    if (isScraperRunning || operationInProgress) {
      console.log('Scraper already running or operation in progress');
      return;
    }

    // This version skips the semester validation since we know semesters are configured
    try {
      setIsScraperRunning(true);
      setIsLoading(true);
      setOperationInProgress(true);
      setStatus('loading');
      setMessage('Running scraper...');
      
      const response = await apiService.runScraper();
      if (response.success && response.data) {
        setTimetableData(response.data);
        setStatus('success');
        setMessage(response.message || 'Scrape completed successfully');
        await checkStatus(); // Update last update time
      } else {
        setStatus('error');
        setMessage(response.error || 'Scrape failed');
        setTimetableData(null);
      }
    } catch (error) {
      console.error('Error running scraper:', error);
      setStatus('error');
      setMessage('Failed to run scraper');
      setTimetableData(null);
    } finally {
      setIsScraperRunning(false);
      setIsLoading(false);
      setOperationInProgress(false);
    }
  };

  const handleSaveSemesters = async (newSemesters: string[]) => {
    if (isSemesterUpdateRunning || operationInProgress) {
      console.log('Semester update already running or operation in progress');
      return;
    }
    
    try {
      setIsSemesterUpdateRunning(true);
      setIsLoading(true);
      setOperationInProgress(true);
      setStatus('loading');
      setMessage('Updating semester settings...');
      
      const response = await apiService.updateSemesters(newSemesters);
      if (response.success) {
        // Reload config to get updated data
        await loadConfig();
        
        // Clear old timetable data since filters changed
        setTimetableData(null);
        
        setStatus('success');
        setMessage(`Successfully updated ${newSemesters.length} allowed semesters. Run scraper to apply new filters.`);
        
        // Automatically run scraper if there are allowed semesters
        if (newSemesters.length > 0) {
          setMessage(`Successfully updated ${newSemesters.length} allowed semesters. Running scraper...`);
          // Small delay to let config state update, then run scraper
          setTimeout(() => {
            runScraperWithSemesters(newSemesters);
          }, 1000);
        }
      } else {
        setStatus('error');
        setMessage(response.error || 'Failed to update semesters');
      }
    } catch (error) {
      console.error('Error updating semesters:', error);
      setStatus('error');
      setMessage('Failed to update semesters');
    } finally {
      setIsSemesterUpdateRunning(false);
      setIsLoading(false);
      setOperationInProgress(false);
    }
  };

  const formatLastUpdate = (timestamp: string | null) => {
    if (!timestamp) return 'Never';
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return 'Unknown';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50/30 to-indigo-50/20 animate-drop-bounce relative">
      {/* Subtle background pattern */}
      <div className="absolute inset-0 opacity-30 bg-gradient-to-r from-transparent via-white/50 to-transparent animate-pulse" style={{animationDuration: '4s'}}></div>
      <div className="relative z-10">
      {/* Header */}
      <header className="bg-white/95 backdrop-blur-sm shadow-lg sticky top-0 z-30 animate-drop-bounce-fast border-b border-blue-100/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between py-3 sm:py-4">
            <div className="flex items-center gap-4 mb-2 sm:mb-0 animate-drop-bounce-fast delay-50">
              <div className="relative">
                <img src="/logoo.svg" alt="Logo" className="h-9 w-9 sm:h-11 sm:w-11 p-1 bg-gradient-to-br from-blue-50 to-indigo-100 rounded-xl transition-all duration-300 hover:scale-110 hover:rotate-3 animate-drop-bounce-fast delay-75 shadow-sm" style={{overflow: 'visible'}} />
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
              </div>
              <div className="flex items-center bg-gradient-to-r from-blue-50 to-indigo-50 rounded-full px-4 py-2 shadow-sm border border-blue-100 transition-all duration-200 hover:shadow-md hover:scale-105 animate-drop-bounce-fast delay-100">
                <span className="text-xs sm:text-sm text-blue-700 font-semibold">Welcome</span>
                <span className="mx-2 text-xs sm:text-sm font-sans text-blue-900 bg-white/70 px-2 py-1 rounded-full">{user?.email}</span>
              </div>
            </div>
            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
              <div className="flex items-center gap-2 text-xs sm:text-sm text-gray-600 bg-gradient-to-r from-gray-50 to-gray-100 rounded-full px-4 py-2 shadow-sm border border-gray-200 transition-all duration-200 hover:shadow-md hover:scale-105 animate-drop-bounce-fast delay-150">
                <img src="/refresh.svg" alt="Last Updated" className="h-4 w-4 mr-1 text-blue-500" />
                <span>Last updated:</span>
                <span className="font-mono text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full text-xs">{formatLastUpdate(lastUpdate)}</span>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={runScraper}
                  disabled={isScraperRunning || operationInProgress}
                  className="inline-flex items-center px-3 sm:px-4 py-2 border-2 border-blue-200 text-xs sm:text-sm font-medium rounded-full shadow-sm text-blue-700 bg-gradient-to-r from-white to-blue-50 hover:from-blue-50 hover:to-blue-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 hover:shadow-md hover:scale-105 animate-drop-bounce-fast delay-200 enhanced-hover"
                >
                  <img src="/refresh.svg" alt="Refresh" className={`h-4 w-4 mr-2 transition-transform duration-300 ${isScraperRunning ? 'animate-spin' : 'hover:rotate-180'}`} />
                  <span className="hidden sm:inline">
                    {isScraperRunning ? 'Scraping...' : isSemesterUpdateRunning ? 'Updating...' : 'Run Scraper'}
                  </span>
                  <span className="sm:hidden">
                    {isScraperRunning ? '⏳' : isSemesterUpdateRunning ? '🔄' : '▶️'}
                  </span>
                </button>
                <button
                  onClick={() => setShowSemesterManager(true)}
                  className={`inline-flex items-center px-3 py-2 border-2 text-xs sm:text-sm font-medium rounded-full text-gray-700 bg-gradient-to-r from-white to-gray-50 hover:from-gray-50 hover:to-gray-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-400 transition-all duration-200 hover:shadow-md hover:scale-105 animate-drop-bounce-fast delay-250 enhanced-hover ${
                    timetableData && config && (!config.semester_filter || config.semester_filter.length === 0) 
                      ? 'border-orange-300 shadow-md bg-gradient-to-r from-orange-50 to-yellow-50' 
                      : 'border-gray-300'
                  }`}
                >
                  <img src="/setting.svg" alt="Settings" className="h-4 w-4 mr-2 transition-transform duration-300 hover:rotate-90" />
                  <span className="hidden sm:inline">Semesters </span>
                  <span className="bg-blue-100 text-blue-700 rounded-full px-2 py-0.5 text-xs font-bold ml-1">
                    {config?.semester_filter?.length || 0}
                  </span>
                </button>
                <div className="relative inline-block animate-drop-bounce-fast delay-300">
                  <button
                    onClick={handleLogoutClick}
                    className="flex items-center space-x-1 text-gray-600 hover:text-red-600 px-3 py-2 rounded-full hover:bg-gradient-to-r hover:from-red-50 hover:to-pink-50 transition-all duration-200 text-xs sm:text-sm border border-gray-200 hover:border-red-200 hover:shadow-md hover:scale-105 enhanced-hover"
                  >
                    <img src="/logout.svg" alt="Logout" className="h-4 w-4 transition-transform duration-300 hover:rotate-12" />
                    <span>Sign Out</span>
                  </button>
                  {showLogoutConfirm && (
                    <div className="absolute right-0 mt-2 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-50 p-4 text-center animate-modal-drop">
                      <div className="text-gray-700 mb-3 text-sm">Are you sure you want to sign out?</div>
                      <div className="flex justify-center gap-2">
                        <button
                          onClick={handleLogoutCancel}
                          className="inline-flex items-center px-3 py-2 border-2 border-gray-400 text-xs sm:text-sm font-medium rounded-full shadow text-gray-700 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-400 transition-colors duration-200 hover:scale-105"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={handleLogoutConfirm}
                          className="inline-flex items-center px-3 py-2 border-2 border-red-400 text-xs sm:text-sm font-medium rounded-full shadow text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-400 transition-colors duration-200 hover:scale-105"
                        >
                          Sign Out
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-4 sm:py-6 px-4 sm:px-6 lg:px-8">
        <div className="space-y-4 sm:space-y-6">
          
          {/* Status Indicator - Always show when config is available */}
          {config && (
            <div>
              <StatusIndicator 
                status={status === 'loading' ? 'loading' : status === 'success' ? 'success' : status === 'warning' ? 'warning' : status === 'error' ? 'error' : 'success'} 
                message={message || (config.semester_filter && config.semester_filter.length > 0 ? `${config.semester_filter.length} semester(s) configured` : 'Ready to configure semesters')} 
              />
            </div>
          )}

          {/* Summary Stats - Always show when config is available */}
          {config && (
            <div>
              {timetableData && !isScraperRunning ? (
                <SummaryStats 
                  data={timetableData} 
                  config={config || undefined} 
                  filteredItems={getFilteredTimetableItems()}
                />
              ) : (
                // Show placeholder stats when no semesters configured
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                  <div className="bg-gradient-to-br from-white to-slate-50/50 overflow-hidden shadow-md rounded-2xl border border-slate-200/50 transition-all duration-300 hover:shadow-lg hover:scale-105 animate-drop-bounce delay-150 enhanced-hover">
                    <div className="p-6 relative opacity-60">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 bg-slate-100 p-3 rounded-2xl border border-slate-200">
                          <img src="/courses.svg" alt="Total Classes" className="w-7 h-7 opacity-50" />
                        </div>
                        <div className="ml-6 w-0 flex-1">
                          <dl>
                            <dt className="text-sm font-medium text-slate-500 truncate">
                              Total Classes
                            </dt>
                            <dd className="text-3xl font-bold text-slate-400 mt-1">
                              0
                            </dd>
                          </dl>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gradient-to-br from-white to-blue-50/50 overflow-hidden shadow-md rounded-xl border border-blue-200/50 transition-all duration-300 hover:shadow-lg hover:scale-105 animate-drop-bounce delay-200 enhanced-hover">
                    <div className="p-4 relative opacity-60">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 bg-blue-100 p-2 rounded-xl border border-blue-200">
                          <img src="/uniqueCourses.svg" alt="Unique Courses" className="w-5 h-5 opacity-50" />
                        </div>
                        <div className="ml-4 w-0 flex-1">
                          <dl>
                            <dt className="text-sm font-medium text-blue-500 truncate">
                              Unique Courses
                            </dt>
                            <dd className="text-2xl font-bold text-blue-400 mt-1">
                              0
                            </dd>
                          </dl>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gradient-to-br from-white to-gray-50/50 overflow-hidden shadow-md rounded-xl border border-gray-200/50 transition-all duration-300 hover:shadow-lg hover:scale-105 animate-drop-bounce delay-250 enhanced-hover">
                    <div className="p-4 relative opacity-60">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 bg-gray-100 p-2 rounded-xl border border-gray-200">
                          <img src="/faculty.svg" alt="Faculty Members" className="w-5 h-5 opacity-50" />
                        </div>
                        <div className="ml-4 w-0 flex-1">
                          <dl>
                            <dt className="text-sm font-medium text-gray-500 truncate">
                              Faculty Members
                            </dt>
                            <dd className="text-2xl font-bold text-gray-400 mt-1">
                              0
                            </dd>
                          </dl>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gradient-to-br from-white to-slate-50/50 overflow-hidden shadow-md rounded-xl border border-slate-200/50 transition-all duration-300 hover:shadow-lg hover:scale-105 animate-drop-bounce delay-300 enhanced-hover">
                    <div className="p-4 relative opacity-60">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 bg-slate-100 p-2 rounded-xl border border-slate-200">
                          <img src="/day.svg" alt="Day" className="w-5 h-5 opacity-50" />
                        </div>
                        <div className="ml-4 w-0 flex-1">
                          <dl>
                            <dt className="text-sm font-medium text-slate-500 truncate">
                              Current Day
                            </dt>
                            <dd className="text-xl font-bold text-slate-400 mt-1">
                              {new Date().toLocaleDateString(undefined, { weekday: 'long' })}
                            </dd>
                          </dl>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="bg-gradient-to-br from-white to-indigo-50/30 overflow-hidden shadow-lg rounded-xl border border-indigo-100 col-span-1 md:col-span-2 lg:col-span-4 transition-all duration-300 hover:shadow-xl hover:scale-105 animate-drop-bounce delay-350 enhanced-hover opacity-60">
                    <div className="p-4 relative">
                      <div className="absolute top-2 right-2 flex gap-1">
                        <div className="w-1 h-1 bg-gray-300 rounded-full animate-pulse"></div>
                        <div className="w-1 h-1 bg-gray-300 rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
                        <div className="w-1 h-1 bg-gray-300 rounded-full animate-pulse" style={{animationDelay: '0.4s'}}></div>
                      </div>
                      <div className="flex items-center mb-3">
                        <div className="bg-gray-100 p-1.5 rounded-lg mr-2">
                          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                          </svg>
                        </div>
                        <span className="font-bold text-gray-500 text-base">Semester Breakdown</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <span className="text-gray-400 text-sm bg-gray-100 px-3 py-1.5 rounded-full border border-gray-200">No semester data available</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Timetable - Only show if config is loaded, semesters are configured, scraper is NOT running, and timetable data is present */}
          {config && !noSemestersConfigured && !isScraperRunning && timetableData && timetableData.items && timetableData.items.length > 0 && (
            <div className="bg-white shadow-lg overflow-hidden rounded-xl border border-gray-100 animate-drop-bounce delay-400 hover:shadow-xl transition-shadow duration-300">
              <div className="px-4 py-4 lg:px-6 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-t-xl">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
                  <div className="mb-2 sm:mb-0 animate-drop-bounce delay-450">
                    <h3 className="text-lg font-semibold text-gray-900 tracking-tight flex items-center gap-2">
                      <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                      Class Schedule
                    </h3>
                  </div>
                  <div className="flex items-center gap-2 animate-drop-bounce delay-500">
                    <div className="flex items-center gap-1 bg-blue-100 rounded-full px-3 py-1 border border-blue-200">
                      <img src="/pulse.svg" alt="Pulse" className="h-4 w-4 text-blue-500" />
                      <span className="text-sm text-blue-700 font-medium">
                        {getFilteredTimetableItems().length} classes
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="p-0 timetable-container">
                <TimetableTable items={getFilteredTimetableItems()} />
              </div>
            </div>
          )}

          {/* Show Configure Semesters card when no semesters are configured and either timetableData exists or scraper is running */}
          {(noSemestersConfigured && (timetableData || isScraperRunning)) && (
            <div className="bg-white rounded-lg shadow p-8 text-center animate-drop-bounce delay-400">
              <div className="text-gray-500 mb-4 animate-drop-bounce delay-450">
                <img src="/setting.svg" alt="Setting" className="mx-auto mb-4 h-16 w-16 text-blue-400 animate-drop-bounce delay-500" />
                <h3 className="text-lg font-medium text-gray-900 mb-2 animate-drop-bounce delay-550">Configure Semesters to View Schedule</h3>
                <p className="text-gray-500 mb-6 animate-drop-bounce delay-600">You have schedule data available, but you need to add semesters to organize and filter your classes properly.</p>
                <button
                  onClick={() => setShowSemesterManager(true)}
                  className="inline-flex items-center px-3 sm:px-4 py-2 border-2 border-gray-400 text-xs sm:text-sm font-medium rounded-full shadow text-gray-700 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-400 transition-all duration-200 hover:shadow-md hover:scale-105 animate-drop-bounce delay-650"
                >
                  <img src="/add.svg" alt="Add" className="h-4 w-4 mr-2" />
                  <span className="hidden sm:inline">Add Semesters</span>
                  <span className="sm:hidden">Add</span>
                </button>
              </div>
            </div>
          )}

          {/* Semester Breakdown removed to avoid duplication */}
        </div>
      </main>

      {/* Minimal Footer */}
      <footer className="bg-transparent border-0">
        <div className="w-full py-1 text-center text-xs text-gray-300">
          &copy; {new Date().getFullYear()} Timetable Wizard v1.0
        </div>
      </footer>

      {/* Semester Manager Modal */}
      <SemesterManager
        isOpen={showSemesterManager}
        onClose={() => setShowSemesterManager(false)}
        currentSemesters={config?.semester_filter || []}
        onSave={handleSaveSemesters}
      />
      </div>
    </div>
  );
}

// Main App component with AuthProvider
function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;