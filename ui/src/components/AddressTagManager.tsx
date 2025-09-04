import React, { useState, useMemo } from 'react';
import { Search, Plus, Trash2, Download, Upload, Tag, AlertCircle, CheckCircle, Edit3, X, Check, ToggleLeft, ToggleRight } from 'lucide-react';
import { useAddressTags } from '../context/AddressTagsContext';
import { formatAddress, formatTag } from '../lib/utils';
import { cn } from '../lib/utils';

interface AddressTagManagerProps {
  className?: string;
}

const AddressTagManager: React.FC<AddressTagManagerProps> = ({ className }) => {
  const {
    getUserTags,
    setUserTag,
    removeUserTag,
    clearUserTags,
    getUserTagCount,
    getSystemTagCount,
    exportUserTags,
    importUserTags,
    getSystemTags,
    isSystemTagDisabled,
    toggleSystemTag,
  } = useAddressTags();

  // Component state
  const [search, setSearch] = useState('');
  const [newAddress, setNewAddress] = useState('');
  const [newTag, setNewTag] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingAddress, setEditingAddress] = useState<string | null>(null);
  const [editingTag, setEditingTag] = useState('');
  const [showSystemTags, setShowSystemTags] = useState(false);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const userTags = getUserTags();
  const systemTags = getSystemTags();

  // Filter tags based on search
  const filteredUserTags = useMemo(() => {
    const entries = Object.entries(userTags);
    if (!search.trim()) return entries;
    
    const searchLower = search.toLowerCase();
    return entries.filter(([address, tag]) => 
      address.includes(searchLower) || tag.toLowerCase().includes(searchLower)
    );
  }, [userTags, search]);

  const filteredSystemTags = useMemo(() => {
    if (!showSystemTags) return [];
    
    const entries = Object.entries(systemTags);
    if (!search.trim()) return entries;
    
    const searchLower = search.toLowerCase();
    return entries.filter(([address, tag]) => 
      address.includes(searchLower) || tag.toLowerCase().includes(searchLower)
    );
  }, [systemTags, search, showSystemTags]);

  // Validation helpers
  const isValidAddress = (address: string): boolean => {
    return /^0x[a-fA-F0-9]{40}$/.test(address);
  };

  const isValidTag = (tag: string): boolean => {
    return tag.trim().length > 0 && tag.trim().length <= 50;
  };

  // Show temporary notification
  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 3000);
  };

  // Handle adding new tag
  const handleAddTag = () => {
    const address = newAddress.trim();
    const tag = newTag.trim();

    if (!isValidAddress(address)) {
      showNotification('error', 'Please enter a valid Ethereum address (0x...)');
      return;
    }

    if (!isValidTag(tag)) {
      showNotification('error', 'Tag must be 1-50 characters long');
      return;
    }

    setUserTag(address, tag);
    setNewAddress('');
    setNewTag('');
    setShowAddForm(false);
    showNotification('success', `Added tag "${formatTag(tag)}" for address`);
  };

  // Handle editing tag
  const startEditing = (address: string, currentTag: string) => {
    setEditingAddress(address);
    setEditingTag(currentTag);
  };

  const saveEdit = () => {
    if (!editingAddress) return;
    
    const tag = editingTag.trim();
    if (!isValidTag(tag)) {
      showNotification('error', 'Tag must be 1-50 characters long');
      return;
    }

    setUserTag(editingAddress, tag);
    setEditingAddress(null);
    setEditingTag('');
    showNotification('success', 'Tag updated successfully');
  };

  const cancelEdit = () => {
    setEditingAddress(null);
    setEditingTag('');
  };

  // Handle deleting tag
  const handleDeleteTag = (address: string, tag: string) => {
    if (confirm(`Delete tag "${formatTag(tag)}" for ${formatAddress(address)}?`)) {
      removeUserTag(address);
      showNotification('success', 'Tag deleted successfully');
    }
  };

  // Handle clearing all tags
  const handleClearAllTags = () => {
    if (confirm(`Delete all ${getUserTagCount()} user tags? This cannot be undone.`)) {
      clearUserTags();
      showNotification('success', 'All user tags cleared');
    }
  };

  // Handle export
  const handleExport = () => {
    try {
      const json = exportUserTags();
      const blob = new Blob([json], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'address-tags.json';
      link.click();
      URL.revokeObjectURL(url);
      showNotification('success', 'Tags exported successfully');
    } catch (error) {
      showNotification('error', 'Failed to export tags');
    }
  };

  // Handle import
  const handleImport = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        const result = importUserTags(content);
        
        if (result.success) {
          showNotification('success', 'Tags imported successfully');
        } else {
          showNotification('error', result.error || 'Failed to import tags');
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  return (
    <div className={cn('space-y-4', className)}>
      {/* Notification */}
      {notification && (
        <div className={cn(
          'flex items-center space-x-2 p-3 rounded-lg text-sm',
          notification.type === 'success' 
            ? 'bg-green-500/20 text-green-400 border border-green-500/30'
            : 'bg-red-500/20 text-red-400 border border-red-500/30'
        )}>
          {notification.type === 'success' ? (
            <CheckCircle className="h-4 w-4 shrink-0" />
          ) : (
            <AlertCircle className="h-4 w-4 shrink-0" />
          )}
          <span>{notification.message}</span>
        </div>
      )}

      {/* Header with statistics */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Tag className="h-4 w-4 text-primary-400" />
            <span className="font-medium text-gray-200">Address Tags</span>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowSystemTags(!showSystemTags)}
            className={cn(
              'px-2 py-1 text-xs rounded border transition-colors',
              showSystemTags
                ? 'border-primary-500 bg-primary-500/20 text-primary-300'
                : 'border-gray-600 text-gray-400 hover:border-gray-500'
            )}
          >
            {showSystemTags ? 'Hide' : 'Show'} System Tags
          </button>
        </div>
      </div>


      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search tags or addresses..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        />
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="flex items-center space-x-2 px-3 py-1.5 bg-primary-500/20 text-primary-300 rounded-lg hover:bg-primary-500/30 transition-colors text-sm"
        >
          <Plus className="h-4 w-4" />
          <span>Add Tag</span>
        </button>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleExport}
            disabled={getUserTagCount() === 0}
            className="flex items-center space-x-1 px-2 py-1 text-xs text-gray-400 hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Download className="h-3 w-3" />
            <span>Export</span>
          </button>
          
          <button
            onClick={handleImport}
            className="flex items-center space-x-1 px-2 py-1 text-xs text-gray-400 hover:text-gray-300 transition-colors"
          >
            <Upload className="h-3 w-3" />
            <span>Import</span>
          </button>

        </div>
      </div>

      {/* Add form */}
      {showAddForm && (
        <div className="p-4 bg-gray-800/50 border border-gray-700 rounded-lg space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Address</label>
              <input
                type="text"
                placeholder="0x..."
                value={newAddress}
                onChange={(e) => setNewAddress(e.target.value)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-primary-500 font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Tag Name</label>
              <input
                type="text"
                placeholder="e.g., My Wallet"
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                maxLength={50}
              />
            </div>
          </div>
          <div className="flex items-center justify-end space-x-2">
            <button
              onClick={() => setShowAddForm(false)}
              className="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-300 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleAddTag}
              disabled={!isValidAddress(newAddress) || !isValidTag(newTag)}
              className="px-3 py-1.5 bg-primary-500 text-white rounded hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
            >
              Add Tag
            </button>
          </div>
        </div>
      )}

      {/* Tags table */}
      <div className="border border-gray-800 rounded-lg overflow-hidden">
        {filteredUserTags.length === 0 && filteredSystemTags.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Tag className="h-12 w-12 text-gray-600 mx-auto mb-3" />
            <p className="text-lg font-medium text-gray-400">No tags found</p>
            <p className="text-sm text-gray-600 mt-1">
              {search ? 'Try adjusting your search terms' : 'Add your first address tag to get started'}
            </p>
          </div>
        ) : (
          <div className="max-h-96 overflow-y-auto">
            <table className="w-full">
              <thead className="bg-gray-800 sticky top-0">
                <tr>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">Type</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">Address</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider">Tag</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-400 uppercase tracking-wider w-20">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {/* User tags */}
                {filteredUserTags.map(([address, tag]) => (
                  <tr key={address} className="hover:bg-gray-800/30">
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-primary-500/20 text-primary-300">
                        User
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-sm text-gray-300">{formatAddress(address)}</span>
                    </td>
                    <td className="px-4 py-3">
                      {editingAddress === address ? (
                        <div className="flex items-center space-x-2">
                          <input
                            type="text"
                            value={editingTag}
                            onChange={(e) => setEditingTag(e.target.value)}
                            className="flex-1 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-primary-500"
                            maxLength={50}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') saveEdit();
                              if (e.key === 'Escape') cancelEdit();
                            }}
                            autoFocus
                          />
                          <button onClick={saveEdit} className="p-1 text-green-400 hover:text-green-300">
                            <Check className="h-3 w-3" />
                          </button>
                          <button onClick={cancelEdit} className="p-1 text-gray-400 hover:text-gray-300">
                            <X className="h-3 w-3" />
                          </button>
                        </div>
                      ) : (
                        <span className="text-sm text-gray-200">{formatTag(tag)}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {editingAddress !== address && (
                        <div className="flex items-center space-x-1">
                          <button
                            onClick={() => startEditing(address, tag)}
                            className="p-1 text-gray-400 hover:text-primary-400 transition-colors"
                            title="Edit tag"
                          >
                            <Edit3 className="h-3 w-3" />
                          </button>
                          <button
                            onClick={() => handleDeleteTag(address, tag)}
                            className="p-1 text-gray-400 hover:text-red-400 transition-colors"
                            title="Delete tag"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}

                {/* System tags */}
                {filteredSystemTags.map(([address, tag]) => {
                  const isDisabled = isSystemTagDisabled(address);
                  return (
                    <tr key={`system-${address}`} className="hover:bg-gray-800/30">
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-gray-500/20 text-gray-400">
                          System
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn(
                          "font-mono text-sm",
                          isDisabled ? "text-gray-500 opacity-60" : "text-gray-300"
                        )}>
                          {formatAddress(address)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn(
                          "text-sm",
                          isDisabled ? "text-gray-600 line-through opacity-60" : "text-gray-400"
                        )}>
                          {formatTag(tag)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => toggleSystemTag(address)}
                          className={cn(
                            "flex items-center space-x-1 px-2 py-1 rounded text-xs transition-colors",
                            isDisabled 
                              ? "text-gray-500 hover:text-gray-400" 
                              : "text-primary-400 hover:text-primary-300"
                          )}
                          title={isDisabled ? "Enable system tag" : "Disable system tag"}
                        >
                          {isDisabled ? (
                            <ToggleLeft className="h-4 w-4" />
                          ) : (
                            <ToggleRight className="h-4 w-4" />
                          )}
                          <span>{isDisabled ? "Disabled" : "Enabled"}</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Help text removed per request */}
    </div>
  );
};

export default AddressTagManager;
