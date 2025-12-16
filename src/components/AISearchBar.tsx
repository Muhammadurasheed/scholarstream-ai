import { useState } from "react";
import { Search, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

interface AISearchBarProps {
  onSearch: (query: string) => void;
}

export const AISearchBar = ({ onSearch }: AISearchBarProps) => {
  const [query, setQuery] = useState("");
  const [isFocused, setIsFocused] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div
        className={`relative glass rounded-2xl transition-all duration-300 ${
          isFocused ? "shadow-lg ring-2 ring-primary/30" : "shadow-md"
        }`}
      >
        <div className="flex items-center gap-3 px-5 py-4">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary/10">
            <Sparkles className="w-5 h-5 text-primary" />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="Ask AI to find scholarships, grants, internships..."
            className="flex-1 bg-transparent border-none outline-none text-foreground placeholder:text-muted-foreground text-base"
          />
          <Button
            type="submit"
            variant="hero"
            size="default"
            className="rounded-xl"
          >
            <Search className="w-4 h-4" />
            Search
          </Button>
        </div>
        
        {/* Subtle gradient line */}
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-1/2 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent" />
      </div>
      
      {/* Quick suggestions */}
      <div className="flex flex-wrap justify-center gap-2 mt-4">
        {["STEM scholarships", "Need-based grants", "Research internships", "Freshman opportunities"].map(
          (suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => {
                setQuery(suggestion);
                onSearch(suggestion);
              }}
              className="px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground bg-secondary/50 hover:bg-secondary rounded-full transition-all duration-200"
            >
              {suggestion}
            </button>
          )
        )}
      </div>
    </form>
  );
};
