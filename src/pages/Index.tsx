import { useState } from "react";
import { Navbar } from "@/components/Navbar";
import { AISearchBar } from "@/components/AISearchBar";
import { CategoryFilter } from "@/components/CategoryFilter";
import { OpportunityCard } from "@/components/OpportunityCard";
import { StatsBar } from "@/components/StatsBar";
import { mockOpportunities } from "@/data/opportunities";
import { Badge } from "@/components/ui/badge";
import { Sparkles } from "lucide-react";

const Index = () => {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const filteredOpportunities = mockOpportunities.filter((opp) => {
    if (selectedCategory && opp.type !== selectedCategory) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        opp.title.toLowerCase().includes(query) ||
        opp.organization.toLowerCase().includes(query) ||
        opp.description.toLowerCase().includes(query) ||
        opp.tags.some((tag) => tag.toLowerCase().includes(query))
      );
    }
    return true;
  });

  const handleSearch = (query: string) => {
    setSearchQuery(query);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Background gradient effects */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-primary/3 rounded-full blur-3xl" />
      </div>

      <Navbar />

      <main className="relative">
        {/* Hero Section */}
        <section className="pt-32 pb-16 px-4">
          <div className="container mx-auto max-w-4xl text-center">
            <Badge variant="outline" className="mb-6 animate-fade-in">
              <Sparkles className="w-3 h-3 mr-1.5" />
              AI-Powered Discovery
            </Badge>
            <h1 
              className="text-4xl md:text-6xl font-bold mb-6 animate-fade-in"
              style={{ animationDelay: "0.1s" }}
            >
              Find Your Perfect{" "}
              <span className="gradient-text">Opportunity</span>
            </h1>
            <p 
              className="text-lg md:text-xl text-muted-foreground mb-10 max-w-2xl mx-auto animate-fade-in"
              style={{ animationDelay: "0.2s" }}
            >
              ScholarStream uses AI to match you with scholarships, grants, internships, 
              and research opportunities tailored to your profile in real-time.
            </p>
            <div 
              className="animate-fade-in"
              style={{ animationDelay: "0.3s" }}
            >
              <AISearchBar onSearch={handleSearch} />
            </div>
          </div>
        </section>

        {/* Stats Section */}
        <section className="py-12 px-4">
          <div className="container mx-auto max-w-5xl">
            <StatsBar />
          </div>
        </section>

        {/* Opportunities Section */}
        <section className="py-12 px-4">
          <div className="container mx-auto max-w-6xl">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
              <div>
                <h2 className="text-2xl md:text-3xl font-bold mb-2">
                  Live Opportunities
                </h2>
                <p className="text-muted-foreground">
                  {filteredOpportunities.length} opportunities matching your criteria
                </p>
              </div>
              <Badge variant="live" className="self-start md:self-auto">
                <span className="w-2 h-2 rounded-full bg-primary mr-1.5" />
                Updated 2 min ago
              </Badge>
            </div>

            <div className="mb-8">
              <CategoryFilter
                selectedCategory={selectedCategory}
                onSelectCategory={setSelectedCategory}
              />
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {filteredOpportunities.map((opportunity, index) => (
                <OpportunityCard
                  key={opportunity.id}
                  opportunity={opportunity}
                  style={{ animationDelay: `${index * 0.1}s` }}
                />
              ))}
            </div>

            {filteredOpportunities.length === 0 && (
              <div className="text-center py-16">
                <p className="text-muted-foreground text-lg">
                  No opportunities found matching your criteria.
                </p>
                <button
                  onClick={() => {
                    setSelectedCategory(null);
                    setSearchQuery("");
                  }}
                  className="mt-4 text-primary hover:underline"
                >
                  Clear filters
                </button>
              </div>
            )}
          </div>
        </section>

        {/* Footer */}
        <footer className="py-12 px-4 border-t border-border">
          <div className="container mx-auto max-w-6xl">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold">
                  Scholar<span className="gradient-text">Stream</span>
                </span>
                <span className="text-muted-foreground text-sm">
                  © 2024
                </span>
              </div>
              <div className="flex items-center gap-6 text-sm text-muted-foreground">
                <a href="#" className="hover:text-foreground transition-colors">
                  Privacy
                </a>
                <a href="#" className="hover:text-foreground transition-colors">
                  Terms
                </a>
                <a href="#" className="hover:text-foreground transition-colors">
                  Contact
                </a>
              </div>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
};

export default Index;
