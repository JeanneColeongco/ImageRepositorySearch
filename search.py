import pymongo
from pymongo import TEXT
from pprint import pprint
import datetime
import csv

myclient = pymongo.MongoClient("mongodb://localhost:27017/") 
# mongod --port 27017 --dbpath mongoDBlog &
# mongo --port 27017

# focusing on the search function
# so not storing images but rather a db of attributes that may be relevant to search 
# has a foreign key to the actual imagesdb
searchdb = myclient["searchdb"]

# in practice, searchdb would likely populate gradually along with the main imagesdb, each time a seller uploads a new image
# this function is for my own use for the sake of this implementation
def load_searchdb():
	global searchdb

	# if search_images collection exists, delete and make a new one
	search_collections = searchdb.list_collection_names()
	if 'search_images' in search_collections:
		search_images = searchdb['search_images']
		search_images.drop()

	search_images = searchdb['search_images']

	# read from file, insert into collection
	with open("searchdb_contents.csv", "r") as file:
		reader = csv.reader(file, delimiter='\t')
		header = next(reader)
		for row in reader: 
			search_document = { header[0]: int(row[0]), # img_id
								header[2]: row[2], # file type
								"text_info": row[1]+' '+ # name
											 row[3]+' '+ # description
											 row[4].replace(",", " ")+' '+ # site_tags
											 row[5].replace(",", " "), # seller_tags
								header[6]: int(row[6]), # buyer_rating
								header[7]: float(row[7]) # price
								}
			searchdb.search_images.insert_one(search_document)

	# index the text information (name, description, site_tags, seller_tags)
	searchdb.search_images.create_index([("text_info", TEXT)])


def search_by_image(img_id):
	global searchdb
	query = searchdb.search_images.find_one({ 'img_id': int(img_id) })
	keywords = query['text_info']
	file_type = query['file_type'].split()
	rating = query['buyer_rating']
	price = query['price']
	search(price, rating, file_type, keywords)


def search(price, rating, file_type, keywords):
	global searchdb
	# search from text/characteristics
	keyword_query = searchdb.search_images.find({ "$text": {"$search": keywords} }, 
												{ 'score': { "$meta": "textScore" } }).sort([('score', {'$meta': 'textScore'})]).limit(10)

	# search from (more) characteristics
	file_type_query = searchdb.search_images.find({ "file_type": { "$in": file_type}},
												  { 'img_id': True, '_id': False })
	
	
	rating_query = searchdb.search_images.find({ "buyer_rating": { "$gte": int(rating)}},
												  { 'img_id': True, '_id': False })

	# price query
	price_img_ids = []
	if price != "":
		price_query = searchdb.search_images.find({ "price": { "$lte": float(price)}},
												  { 'img_id': True, '_id': False })
		for p in price_query:
			price_img_ids.append(p['img_id'])

	# img_ids are the foreign key into imagesdb, which contains the actual images to display
	# this is the only info we need as a result of the search
	file_type_img_ids = []
	keyword_img_ids = []
	rating_img_ids = []
	
	for r in rating_query:
		rating_img_ids.append(r['img_id'])
	for f in file_type_query:
		file_type_img_ids.append(f['img_id'])
	for k in keyword_query:
		keyword_img_ids.append(k['img_id'])
	
	# narrow down
	results = []
	for i in rating_img_ids:
		if len(file_type_img_ids)==0 or i in file_type_img_ids:
			if len(price_img_ids)==0 or i in price_img_ids:
				if len(keyword_img_ids)== 0 or i in keyword_img_ids:
					results.append(i)

	print("You have " + str(len(results)) + " results.")
	for img_id in results:
		print(img_id)

	take_input()


def take_input():
	img_id = input("Provide img_id if you wish to search by image.\nType 'q' if you wish to quit\nOtherwise, hit Enter for more search options: ")
	# assume users can only search by an image that's in the database to find similar images
	# when searching by an image, all that is needed is the image id, the rest can be retrieved from there
	if img_id == "q":
		exit()
	elif img_id != "":
		search_by_image(img_id)
		return

	# a separate field because for security there should be a limit on the file types that can be uploaded
	# so a checkbox interface is likely a reasonable expectation and the flags for those checkboxes can be fed into here
	file_type = input("Prefered image file type(s), space-separated: ").split()
	# if none is provided, all types will be shown

	price = input("Maximum price: ")
	# if none is provided, all prices will be shown

	# similar to price range filter (except will output results gte instead of lte)
	rating = input("Prefered rating: (1 --> 5) ")
	# if none is provided, all ratings will be shown
	if rating=="" or (int(rating) < 1 and int(rating) > 5):
		rating = 1
	
	# assumes users search like on any search engine, with spaces between words
	keywords = input("Please input your search terms: ")
	# if none is provided all images will be shown

	search(price, rating, file_type, keywords)
	return


def main():
	global searchdb
	load_searchdb()
	contents = searchdb.search_images.find()
	for i in contents:
		pprint(i)

	take_input()


if __name__ == "__main__":
    main()