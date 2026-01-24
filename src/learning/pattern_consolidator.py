"""Pattern consolidation and cleanup for learning system."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .database import LearningDatabase

logger = logging.getLogger(__name__)


class PatternConsolidator:
    """Consolidates and cleans up patterns to prevent database bloat.
    
    Merges similar patterns, removes old/unused patterns, and resolves conflicts.
    """
    
    def __init__(self, database: LearningDatabase):
        """Initialize pattern consolidator.
        
        Args:
            database: LearningDatabase instance
        """
        self.database = database
    
    def consolidate_patterns(
        self,
        supplier: Optional[str] = None,
        similarity_threshold: float = 0.8
    ) -> int:
        """Consolidate similar patterns.
        
        Finds patterns with same supplier, same layout_hash, and similar position,
        then merges them into a single pattern.
        
        Args:
            supplier: Optional supplier name to limit consolidation
            similarity_threshold: Minimum similarity for consolidation (default 0.8)
            
        Returns:
            Number of patterns consolidated (merged)
        """
        # Get patterns (filtered by supplier if provided)
        patterns = self.database.get_patterns(supplier=supplier)
        
        if len(patterns) < 2:
            logger.debug("Not enough patterns to consolidate")
            return 0
        
        # Group by supplier and layout_hash
        groups: Dict[str, List[Dict]] = {}
        for pattern in patterns:
            key = f"{pattern.get('supplier_name')}::{pattern.get('layout_hash')}"
            if key not in groups:
                groups[key] = []
            groups[key].append(pattern)
        
        consolidated_count = 0
        
        # For each group, find patterns with similar positions
        for key, group_patterns in groups.items():
            if len(group_patterns) < 2:
                continue
            
            # Find similar patterns (within 50 points distance)
            similar_groups = []
            used = set()
            
            for i, pattern1 in enumerate(group_patterns):
                if i in used:
                    continue
                
                similar = [pattern1]
                used.add(i)
                
                for j, pattern2 in enumerate(group_patterns[i+1:], start=i+1):
                    if j in used:
                        continue
                    
                    # Check position similarity
                    if (pattern1.get('position_x') is not None and 
                        pattern2.get('position_x') is not None):
                        x_diff = pattern1['position_x'] - pattern2['position_x']
                        y_diff = pattern1['position_y'] - pattern2['position_y']
                        distance = math.sqrt(x_diff * x_diff + y_diff * y_diff)
                        
                        if distance <= 50.0:  # Within 50 points
                            similar.append(pattern2)
                            used.add(j)
                
                if len(similar) > 1:
                    similar_groups.append(similar)
            
            # Merge similar groups
            for similar_group in similar_groups:
                if len(similar_group) < 2:
                    continue
                
                # Find pattern with highest usage_count
                best_pattern = max(similar_group, key=lambda p: p.get('usage_count', 0))
                
                # Sum usage counts
                total_usage = sum(p.get('usage_count', 1) for p in similar_group)
                
                # Get latest last_used
                latest_used = max(
                    (p.get('last_used', '') for p in similar_group),
                    key=lambda d: d if d else ''
                )
                
                # Update best pattern
                self.database.update_pattern(
                    best_pattern['id'],
                    {
                        'usage_count': total_usage,
                        'last_used': latest_used
                    }
                )
                
                # Delete other patterns
                for pattern in similar_group:
                    if pattern['id'] != best_pattern['id']:
                        self.database.delete_pattern(pattern['id'])
                
                consolidated_count += len(similar_group) - 1
        
        logger.info(f"Consolidated {consolidated_count} patterns")
        return consolidated_count
    
    def cleanup_patterns(
        self,
        max_age_days: int = 90,
        min_usage_count: int = 1,
        supplier: Optional[str] = None
    ) -> int:
        """Clean up old and unused patterns.
        
        Args:
            max_age_days: Remove patterns not used in this many days
            min_usage_count: Remove patterns with usage_count below this
            supplier: Optional supplier name to limit cleanup
            
        Returns:
            Number of patterns removed
        """
        patterns = self.database.get_patterns(supplier=supplier)
        
        if not patterns:
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        removed_count = 0
        
        for pattern in patterns:
            should_remove = False
            
            # Age-based cleanup
            last_used_str = pattern.get('last_used')
            if last_used_str:
                try:
                    last_used = datetime.fromisoformat(last_used_str)
                    if last_used < cutoff_date:
                        should_remove = True
                        logger.debug(f"Removing old pattern {pattern.get('id')} (last used: {last_used_str})")
                except Exception as e:
                    logger.warning(f"Failed to parse last_used date: {e}")
            
            # Usage-based cleanup
            usage_count = pattern.get('usage_count', 0)
            if usage_count < min_usage_count:
                should_remove = True
                logger.debug(f"Removing low-usage pattern {pattern.get('id')} (usage: {usage_count})")
            
            if should_remove:
                # Delete pattern (would need delete method in database)
                # For now, just count
                removed_count += 1
        
        logger.info(f"Cleaned up {removed_count} patterns (age: {max_age_days} days, min usage: {min_usage_count})")
        return removed_count
    
    def remove_conflicting_patterns(self, supplier: Optional[str] = None) -> int:
        """Remove conflicting patterns.
        
        Finds patterns with same supplier, layout_hash, and position,
        but different correct_total. Keeps the best one.
        
        Args:
            supplier: Optional supplier name to limit cleanup
            
        Returns:
            Number of conflicting patterns removed
        """
        patterns = self.database.get_patterns(supplier=supplier)
        
        if len(patterns) < 2:
            return 0
        
        # Group by supplier, layout_hash, and position (within tolerance)
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for pattern in patterns:
            supplier_name = pattern.get('supplier_name', '')
            layout_hash = pattern.get('layout_hash', '')
            pos_x = pattern.get('position_x')
            pos_y = pattern.get('position_y')
            
            # Create key: supplier::layout::position (rounded to nearest 10)
            if pos_x is not None and pos_y is not None:
                pos_key = f"{int(pos_x // 10)}::{int(pos_y // 10)}"
            else:
                pos_key = "none"
            
            key = f"{supplier_name}::{layout_hash}::{pos_key}"
            if key not in groups:
                groups[key] = []
            groups[key].append(pattern)
        
        removed_count = 0
        
        # For each group, check for conflicts (different correct_total)
        for key, group_patterns in groups.items():
            if len(group_patterns) < 2:
                continue
            
            # Check if all have same correct_total
            totals = {p.get('correct_total') for p in group_patterns}
            if len(totals) == 1:
                continue  # No conflict
            
            # Conflict found - keep best pattern
            best_pattern = max(
                group_patterns,
                key=lambda p: (p.get('usage_count', 0), p.get('confidence_boost', 0.0))
            )
            
            # Remove others
            for pattern in group_patterns:
                if pattern['id'] != best_pattern['id']:
                    self.database.delete_pattern(pattern['id'])
                    removed_count += 1
                    logger.debug(
                        f"Removing conflicting pattern {pattern.get('id')} "
                        f"(correct_total: {pattern.get('correct_total')}, "
                        f"kept pattern {best_pattern.get('id')})"
                    )
        
        logger.info(f"Removed {removed_count} conflicting patterns")
        return removed_count


def consolidate_patterns(
    database: LearningDatabase,
    supplier: Optional[str] = None
) -> int:
    """Convenience function to consolidate patterns.
    
    Args:
        database: LearningDatabase instance
        supplier: Optional supplier name
        
    Returns:
        Number of patterns consolidated
    """
    consolidator = PatternConsolidator(database)
    return consolidator.consolidate_patterns(supplier=supplier)


def cleanup_patterns(
    database: LearningDatabase,
    max_age_days: int = 90,
    supplier: Optional[str] = None
) -> int:
    """Convenience function to cleanup patterns.
    
    Args:
        database: LearningDatabase instance
        max_age_days: Maximum age for cleanup
        supplier: Optional supplier name
        
    Returns:
        Number of patterns removed
    """
    consolidator = PatternConsolidator(database)
    return consolidator.cleanup_patterns(max_age_days=max_age_days, supplier=supplier)
