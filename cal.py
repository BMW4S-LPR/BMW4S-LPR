class Solution:
	def lengthOfLongestSubstring(self, s):
		"""
		:type s: str
		:rtype: int
		"""
		ans = 0
		for i in range(len(s)):
			mp = {}
			tmpans = 0
			for j in range(i, len(s)):
				if mp.get(s[j], None) == None:
					mp[s[j]] = 1
					tmpans += 1
				else:
					ans = max(ans, tmpans)
					break

		return ans