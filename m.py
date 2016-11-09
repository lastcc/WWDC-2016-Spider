import requests
import json
import scrapy
from scrapy.crawler import CrawlerProcess


class Writer(object):
    """
    This class converts data to compatible format so that previous written downloader could be reused.
    """
    L = []

    def add_item(self, item):
        assert isinstance(item, MyItem), 'Expect MyItem, got %r' % type(item)
        self.L.append(item)

    def convert_to_compatible(self):
        r = {}

        for each in self.L:
            d = {
                'title': each['name'],
                'code': list(map(lambda xxx: xxx[1], each['samples'])),
                'HD': each['HDVideo'],
                'this_page': each['URL'],
                'SD': each['SDVideo'],
                'pdf': list(map(lambda xxx: xxx[1], each['slides']))
            }

            section = each['section']
            if section in r:
                r[section].append(d)
            else:
                r[section] = [d]

        with open('recs.txt', 'w') as f:
            f.write(str(r))

        print('done.')


class MyItem(scrapy.Item):
    section = scrapy.Field()  # section name
    URL = scrapy.Field()      # video URL
    name = scrapy.Field()     # video title
    samples = scrapy.Field()  # sample code URLs
    slides = scrapy.Field()   # PDF links
    HDVideo = scrapy.Field()  # HD Video URL
    SDVideo = scrapy.Field()  # HD Video URL


class WWDCSpider(scrapy.Spider):
    name = 'WWDC Spider'
    base_URL = 'https://developer.apple.com/videos/wwdc2016'
    start_urls = [base_URL]

    def parse(self, response):
        sections = response.xpath(
            '//section[@class="all-content padding-bottom"]/descendant::li[@class="collection-focus-group " and @id]')
        for index, section in enumerate(sections):
            section_name = '%s. %s' % (index, section.xpath('.//span[@class="font-bold"]/text()').extract_first())
            for each in section.xpath('.//li[@class="collection-item "]'):
                name = each.xpath('.//a[contains(@href, "/videos/play/wwdc2016/")]/h5/text()').extract_first()
                relative_URL = each.xpath('.//a[contains(@href, "/videos/play/wwdc2016/")]/@href').extract_first()
                URL = '%s%s' % (self.base_URL, relative_URL)

                yield scrapy.Request(URL, callback=self.parse_each, meta={'section_name': section_name,
                                                                          'name': name,
                                                                          'URL': URL})

    def parse_each(self, response):
        URL = response.meta['URL']
        section_name = response.meta['section_name']
        name = response.meta['name']

        def find_download_URL(sample_page):
            book = '%s/book.json' % sample_page
            J = json.loads(requests.get(book).text)
            sampleCode = J['sampleCode']
            return '%s/%s' % (sample_page, sampleCode)

        samples = []
        for selector in response.xpath('//li[@class="sample-code"]/a'):
            sample_URL = 'https://developer.apple.com%s' % selector.xpath('@href').extract_first()
            sample_name = selector.xpath('text()').extract_first()

            sample_URL = find_download_URL(sample_URL)
            samples.append([sample_name, sample_URL])

        HD_Video = response.xpath('//li[@class="video"]//li/a[text()="HD Video"]/@href').extract_first()
        SD_Video = response.xpath('//li[@class="video"]//li/a[text()="SD Video"]/@href').extract_first()

        PDFs = []
        for selector in response.xpath('//li[@class="document"]/a'):
            PDF_name = selector.xpath('text()').extract_first()
            PDF_URL = selector.xpath('@href').extract_first()
            PDFs.append([PDF_name, PDF_URL])

        item = MyItem()
        item['name'] = name
        item['URL'] = URL
        item['section'] = section_name
        item['samples'] = samples
        item['slides'] = PDFs
        item['HDVideo'] = HD_Video
        item['SDVideo'] = SD_Video

        global writer
        writer.add_item(item)

        yield item  # scrapy runspider m.py -o result.json


writer = Writer()
process = CrawlerProcess({
    'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)',
})

process.crawl(WWDCSpider)
process.start()
writer.convert_to_compatible()
