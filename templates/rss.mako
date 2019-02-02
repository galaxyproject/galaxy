<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>${title}</title>
        <link>${link}</link>
        <pubDate>${pubdate}</pubDate>
        <description>${description}</description>
        <language>en-US</language>
        <ttl>60</ttl>
        <docs>http://cyber.law.harvard.edu/rss/rss.html</docs>
        %for item in items:
            <item>
                <pubDate>${item['pubdate']}</pubDate>
                <title>${item['title']}</title>
                <link>${item['link']}</link>
                <guid>${item['guid']}</guid>
                <description>
                    ${item['description']}
                </description>
            </item>
        %endfor
    </channel>
</rss>
