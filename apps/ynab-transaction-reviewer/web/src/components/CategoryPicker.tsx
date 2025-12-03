'use client';

import * as React from 'react';
import { Check, ChevronDown, Search } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type { CategoryGroup, Category } from '@/lib/types';

interface CategoryPickerProps {
  categories: CategoryGroup[];
  value: string | null;
  onChange: (categoryId: string) => void;
  disabled?: boolean;
}

export function CategoryPicker({
  categories,
  value,
  onChange,
  disabled = false,
}: CategoryPickerProps) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');
  const containerRef = React.useRef<HTMLDivElement>(null);

  // Find selected category name
  const selectedCategory = React.useMemo(() => {
    for (const group of categories) {
      const found = group.categories.find(c => c.id === value);
      if (found) return found;
    }
    return null;
  }, [categories, value]);

  // Filter categories based on search
  const filteredCategories = React.useMemo(() => {
    if (!search) return categories;
    const lowerSearch = search.toLowerCase();
    return categories
      .map(group => ({
        ...group,
        categories: group.categories.filter(
          c =>
            c.name.toLowerCase().includes(lowerSearch) ||
            group.name.toLowerCase().includes(lowerSearch)
        ),
      }))
      .filter(group => group.categories.length > 0);
  }, [categories, search]);

  // Close dropdown when clicking outside
  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
    }
  };

  return (
    <div ref={containerRef} className="relative" onKeyDown={handleKeyDown}>
      <Button
        variant="outline"
        role="combobox"
        aria-expanded={isOpen}
        disabled={disabled}
        className="w-full justify-between"
        onClick={() => setIsOpen(!isOpen)}
      >
        {selectedCategory ? selectedCategory.name : 'Select category...'}
        <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
      </Button>

      {isOpen && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover shadow-lg">
          {/* Search input */}
          <div className="flex items-center border-b px-3">
            <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
            <input
              type="text"
              placeholder="Search categories..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="flex h-10 w-full bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground"
              autoFocus
            />
          </div>

          {/* Category list */}
          <div className="max-h-[300px] overflow-y-auto p-1">
            {filteredCategories.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No categories found.
              </p>
            ) : (
              filteredCategories.map((group) => (
                <div key={group.id}>
                  {/* Group header */}
                  <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                    {group.name}
                  </div>
                  {/* Group categories */}
                  {group.categories
                    .filter(c => !c.hidden)
                    .map((category) => (
                      <button
                        key={category.id}
                        onClick={() => {
                          onChange(category.id);
                          setIsOpen(false);
                          setSearch('');
                        }}
                        className={cn(
                          'flex w-full cursor-pointer items-center rounded-sm px-2 py-1.5 text-sm hover:bg-accent',
                          category.id === value && 'bg-accent'
                        )}
                      >
                        <Check
                          className={cn(
                            'mr-2 h-4 w-4',
                            category.id === value ? 'opacity-100' : 'opacity-0'
                          )}
                        />
                        {category.name}
                      </button>
                    ))}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
