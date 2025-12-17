import { useState, useMemo, useEffect } from 'react';
import { Target, DollarSign, Clock, FileText, Sparkles, Search, Wifi, WifiOff } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { StatsCard } from '@/components/dashboard/StatsCard';
import { FinancialImpactWidget } from '@/components/dashboard/FinancialImpactWidget';
import { QuickActionsWidget } from '@/components/dashboard/QuickActionsWidget';
import { ActivityFeedWidget } from '@/components/dashboard/ActivityFeedWidget';
import { PriorityAlertsSection } from '@/components/dashboard/PriorityAlertsSection';
import { OpportunityGrid } from '@/components/dashboard/OpportunityGrid';
import { PaginatedOpportunitySection } from '@/components/dashboard/PaginatedOpportunitySection';
import { MobileBottomNav } from '@/components/dashboard/MobileBottomNav';
import { FloatingChatAssistant } from '@/components/dashboard/FloatingChatAssistant';
import { ViewToggle } from '@/components/dashboard/ViewToggle';
import { LocationFilter, LocationScope, filterByLocation, sortByLocationRelevance } from '@/components/dashboard/LocationFilter';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { useScholarships } from '@/hooks/useScholarships';
import { useAuth } from '@/contexts/AuthContext';
import { Skeleton } from '@/components/ui/skeleton';
import { formatCurrency, calculateDaysUntilDeadline } from '@/utils/scholarshipUtils';
import { UserProfile } from '@/types/scholarship';
import { matchingEngine } from '@/services/matchingEngine';
import { useRealtimeOpportunities } from '@/hooks/useRealtimeOpportunities';
import { Badge } from '@/components/ui/badge';
import { db } from '@/lib/firebase';
import { doc, getDoc } from 'firebase/firestore';
import { NotificationPill } from '@/components/dashboard/NotificationPill';
import { SkeletonCard } from '@/components/ui/SkeletonCard';

const Dashboard = () => {
  const { user } = useAuth();
  const location = useLocation();
  const {
    scholarships,
    stats,
    loading,
    discoveryStatus,
    discoveryProgress,
    triggerDiscovery,
  } = useScholarships();

  const [searchQuery, setSearchQuery] = useState('');
  const [view, setView] = useState<'grid' | 'list'>('grid');
  const [activeTab, setActiveTab] = useState('all');
  const [locationScope, setLocationScope] = useState<LocationScope>('all');

  // Real-time WebSocket connection
  const {
    connected: wsConnected,
    opportunities: realtimeOpportunities,
    newOpportunitiesCount,
    clearNewOpportunitiesCount,
    flushBuffer // Export flush function
  } = useRealtimeOpportunities();

  // User profile state - fetched from Firestore with localStorage fallback
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);

  // Fetch user profile from Firestore on mount
  useEffect(() => {
    const fetchProfile = async () => {
      if (!user?.uid) return;

      try {
        // First, try Firestore (source of truth)
        if (db) {
          const userDoc = await getDoc(doc(db, 'users', user.uid));
          if (userDoc.exists()) {
            const userData = userDoc.data();
            const profile = userData?.profile;

            if (profile) {
              const formattedProfile: UserProfile = {
                name: `${profile.firstName || profile.name || ''} ${profile.lastName || ''}`.trim(),
                academic_status: profile.academicStatus || profile.academic_status,
                school: profile.school,
                gpa: profile.gpa,
                major: profile.major,
                interests: profile.interests || [],
                financial_need: profile.financialNeed || profile.financial_need || 0,
                country: profile.country,
                state: profile.state,
                city: profile.city,
              };
              setUserProfile(formattedProfile);
              // Sync to localStorage for offline access
              localStorage.setItem('scholarstream_profile', JSON.stringify(profile));
              console.log('✅ Profile loaded from Firestore');
              return;
            }
          }
        }
      } catch (error) {
        console.warn('Could not fetch profile from Firestore, using localStorage fallback:', error);
      }

      // Fallback to localStorage if Firestore fails
      const profileData = localStorage.getItem('scholarstream_profile');
      if (profileData) {
        try {
          const profile = JSON.parse(profileData);
          const userProfileData: UserProfile = {
            name: `${profile.firstName || ''} ${profile.lastName || ''}`.trim(),
            academic_status: profile.academicStatus || profile.academic_status,
            school: profile.school,
            gpa: profile.gpa,
            major: profile.major,
            interests: profile.interests || [],
            financial_need: profile.financialNeed || profile.financial_need || 0,
            country: profile.country,
            state: profile.state,
            city: profile.city,
          };
          setUserProfile(userProfileData);
          console.log('📱 Profile loaded from localStorage');
        } catch (e) {
          console.error('Error parsing profile from localStorage:', e);
        }
      }
    };

    fetchProfile();
  }, [user?.uid]);

  // Apply matching engine ranking to scholarships (merge real-time + cached)
  const rankedScholarships = useMemo(() => {
    // Merge real-time and cached scholarships
    const allScholarships = [...realtimeOpportunities, ...scholarships];

    {/* Deduplicate by content (URL or Title) since IDs might initially be unstable timestamps */ }
    const uniqueScholarships = Array.from(
      new Map(allScholarships.map(s => [s.source_url || s.name, s])).values()
    );

    if (!userProfile || uniqueScholarships.length === 0) return uniqueScholarships;

    // Use the matching engine to rank opportunities
    return matchingEngine.rankOpportunities(uniqueScholarships, userProfile as any);
  }, [scholarships, realtimeOpportunities, userProfile]);

  // Trigger discovery if coming from onboarding
  useEffect(() => {
    const state = location.state as { triggerDiscovery?: boolean; profileData?: any };
    if (state?.triggerDiscovery && state?.profileData && user?.uid) {
      const userProfileData: UserProfile = {
        name: `${state.profileData.firstName} ${state.profileData.lastName}`,
        academic_status: state.profileData.academicStatus,
        school: state.profileData.school,
        year: state.profileData.year,
        gpa: state.profileData.gpa,
        major: state.profileData.major,
        graduation_year: state.profileData.graduationYear,
        background: state.profileData.background,
        financial_need: state.profileData.financialNeed,
        interests: state.profileData.interests,
        country: state.profileData.country,
        state: state.profileData.state,
        city: state.profileData.city,
      };

      triggerDiscovery(userProfileData);

      // Clear the state to prevent re-triggering on refresh
      window.history.replaceState({}, document.title);
    }
  }, [location.state, user, triggerDiscovery]);

  const getUserName = () => {
    const profileData = localStorage.getItem('scholarstream_profile');
    if (profileData) {
      try {
        const profile = JSON.parse(profileData);
        if (profile.firstName) return profile.firstName;
      } catch (e) {
        console.error('Error parsing profile data:', e);
      }
    }
    return user?.name?.split(' ')[0] || 'there';
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  // Combine and deduplicate opportunities
  const allOpportunities = useMemo(() => {
    const combined = [...realtimeOpportunities, ...scholarships];
    const unique = new Map();
    combined.forEach(item => unique.set(item.id, item));
    return Array.from(unique.values());
  }, [realtimeOpportunities, scholarships]);

  // Smart grouping with Search & Location logic
  const groupedOpportunities = useMemo(() => {
    let filtered = allOpportunities;

    // 1. Search Filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        s =>
          s.name.toLowerCase().includes(query) ||
          s.organization.toLowerCase().includes(query) ||
          s.description.toLowerCase().includes(query) ||
          s.tags.some(tag => tag.toLowerCase().includes(query))
      );
    }

    // 2. Location Filter
    if (locationScope !== 'all' && userProfile) {
      filtered = filterByLocation(filtered, locationScope, userProfile.country, userProfile.state);
    }

    // 3. User Sorting (Location Relevance)
    if (userProfile) {
      filtered = sortByLocationRelevance(filtered, userProfile.country, userProfile.state);
    }

    return {
      all: filtered,
      urgent: filtered.filter(o => o.priority_level === 'URGENT' || o.priority_level === 'urgent'),
      highMatch: filtered.filter(o => o.match_score >= 85),
      byType: {
        scholarships: filtered.filter(o => !['devpost', 'gitcoin', 'kaggle', 'mlh'].includes(o.source_type || '')),
        hackathons: filtered.filter(o => o.source_type === 'devpost' || o.source_type === 'mlh'),
        bounties: filtered.filter(o => o.source_type === 'gitcoin'),
        competitions: filtered.filter(o => o.source_type === 'kaggle')
      }
    };
  }, [allOpportunities, searchQuery, locationScope, userProfile]);

  // Get current tab opportunities
  const getCurrentTabOpportunities = () => {
    switch (activeTab) {
      case 'scholarships':
        return groupedOpportunities.byType.scholarships;
      case 'hackathons':
        return groupedOpportunities.byType.hackathons;
      case 'bounties':
        return groupedOpportunities.byType.bounties;
      case 'competitions':
        return groupedOpportunities.byType.competitions;
      default:
        return groupedOpportunities.all;
    }
  };

  // Display opportunities for current tab
  const displayOpportunities = getCurrentTabOpportunities();

  // Skeleton renderer for loading states
  const renderSkeletons = (count: number = 6) => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );


  if (loading || (discoveryStatus === 'processing' && rankedScholarships.length === 0)) {
    return (
      <div className="min-h-screen bg-background">
        <DashboardHeader />
        <div className="container py-8">
          {/* Hero Section with Discovery Status */}
          <div className="mb-8 rounded-xl bg-gradient-to-r from-primary/15 via-primary/8 to-background p-8 border border-primary/20">
            <h1 className="mb-2 text-3xl font-bold text-foreground">
              {getGreeting()}, {getUserName()}! 👋
            </h1>
            {discoveryStatus === 'processing' ? (
              <div className="flex items-center gap-3 mt-4">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent"></div>
                <p className="text-primary font-semibold">
                  Discovering opportunities for you... ({discoveryProgress}%)
                </p>
              </div>
            ) : (
              <p className="text-foreground/70 font-medium">Loading your dashboard...</p>
            )}
          </div>

          <div className="space-y-8">
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-32" />
              ))}
            </div>
            <Skeleton className="h-96 w-full" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-20 lg:pb-8 relative">
      <DashboardHeader />

      {/* Dynamic Notification Pill */}
      <NotificationPill
        count={newOpportunitiesCount}
        onClick={flushBuffer}
      />

      <main className="container py-8">
        <div className="flex gap-8">
          {/* Main Content */}
          <div className="flex-1 min-w-0">
            {/* Hero Section */}
            <div className="mb-8 rounded-xl bg-gradient-to-r from-primary/15 via-primary/8 to-background p-8 border border-primary/20">
              <h1 className="mb-2 text-3xl font-bold text-foreground">
                {getGreeting()}, {getUserName()}! 👋
              </h1>
              <p className="text-foreground/70 font-medium">
                You have <span className="text-primary font-bold">{groupedOpportunities.urgent.length} urgent opportunities</span> and <span className="text-primary font-bold">{groupedOpportunities.highMatch.length} excellent matches</span> waiting.
              </p>
            </div>

            {/* WebSocket Status Indicator (Subtle) */}
            <div className="mb-6 flex items-center gap-2 text-xs text-muted-foreground">
              {wsConnected ? (
                <span className="flex items-center gap-1.5 text-green-600 bg-green-500/10 px-2 py-1 rounded-full">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                  </span>
                  Live Stream Active
                </span>
              ) : (
                <span className="flex items-center gap-1.5 opacity-50">
                  <WifiOff className="w-3 h-3" /> Connecting...
                </span>
              )}
            </div>


            {/* Stats Row */}
            <div className="mb-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              <StatsCard
                icon={Target}
                value={stats.opportunities_matched}
                label="Scholarships Found"
                iconColor="text-primary"
              />
              <StatsCard
                icon={DollarSign}
                value={formatCurrency(stats.total_value)}
                label="Total Potential Value"
                iconColor="text-success"
              />
              <StatsCard
                icon={Clock}
                value={stats.urgent_deadlines}
                label="Urgent This Week"
                iconColor={stats.urgent_deadlines > 0 ? 'text-destructive' : 'text-muted-foreground'}
              />
              <StatsCard
                icon={FileText}
                value={stats.applications_started}
                label="In Progress"
                iconColor="text-info"
              />
            </div>

            {/* Top Matches Section */}
            {groupedOpportunities.highMatch.length > 0 && (
              <section className="mb-10">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="text-2xl font-bold flex items-center gap-2">
                      <Target className="w-6 h-6 text-primary" />
                      Your Best Matches
                    </h2>
                    <p className="text-muted-foreground">
                      Opportunities with 85%+ match score based on your profile
                    </p>
                  </div>
                </div>
                <OpportunityGrid opportunities={groupedOpportunities.highMatch.slice(0, 4)} view="grid" />
              </section>
            )}

            {/* Priority Alerts */}
            <PriorityAlertsSection urgentScholarships={groupedOpportunities.urgent} />


            {/* Categorized Opportunities */}
            <section id="opportunities-section">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-4">
                <h2 className="text-2xl font-bold">Explore Opportunities</h2>
                <div className="flex items-center gap-3 flex-wrap">
                  <LocationFilter
                    userCountry={userProfile?.country}
                    userState={userProfile?.state}
                    selectedScope={locationScope}
                    onScopeChange={setLocationScope}
                  />
                  <div className="relative w-full sm:w-72">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                    <Input
                      placeholder="Search scholarships..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-9"
                    />
                  </div>
                  <ViewToggle view={view} onViewChange={setView} />
                </div>
              </div>

              <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                <TabsList className="w-full justify-start mb-6 overflow-x-auto">
                  <TabsTrigger value="all">All ({groupedOpportunities.all.length})</TabsTrigger>
                  <TabsTrigger value="scholarships">Scholarships ({groupedOpportunities.byType.scholarships.length})</TabsTrigger>
                  <TabsTrigger value="hackathons">Hackathons ({groupedOpportunities.byType.hackathons.length})</TabsTrigger>
                  <TabsTrigger value="bounties">Bounties ({groupedOpportunities.byType.bounties.length})</TabsTrigger>
                  <TabsTrigger value="competitions">Competitions ({groupedOpportunities.byType.competitions.length})</TabsTrigger>
                </TabsList>

                {/* Main Content Area */}
                {loading && scholarships.length === 0 ? (
                  renderSkeletons()
                ) : (
                  <div className="min-h-[400px]">
                    {/* Zero State or Grid */}
                    {displayOpportunities.length === 0 ? (
                      <div className="text-center py-20 bg-muted/10 rounded-xl border-2 border-dashed border-muted">
                        <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-4">
                          <Search className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <h3 className="text-lg font-semibold">No opportunities found</h3>
                        <p className="text-muted-foreground max-w-sm mx-auto mt-2">
                          Try adjusting your filters or check back later. The Cortex Engine is always hunting.
                        </p>
                      </div>
                    ) : (
                      view === 'grid' ? (
                        <OpportunityGrid opportunities={displayOpportunities} />
                      ) : (
                        <PaginatedOpportunitySection
                          opportunities={displayOpportunities}
                          itemsPerPage={10}
                          view="list"
                        />
                      )
                    )}
                  </div>
                )}
              </Tabs>
            </section>
          </div >

          {/* Right Sidebar - Desktop Only */}
          < aside className="hidden xl:block w-80 space-y-6 shrink-0" >
            <FinancialImpactWidget stats={stats} />
            <QuickActionsWidget />
            <ActivityFeedWidget />
          </aside >
        </div >
      </main >

      {/* Mobile Bottom Navigation */}
      < MobileBottomNav />

      {/* Floating AI Chat Assistant */}
      < FloatingChatAssistant />
    </div >
  );
};

export default Dashboard;