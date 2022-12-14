# -*- coding: utf-8 -*-


# !pip install flask-ngrok
# !pip install flask_mysqldb
# !pip install pyngrok

import pandas as pd

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from random import *
import random


from flask import Flask, jsonify,request,json
from flask_mysqldb import MySQL
from flask_ngrok import run_with_ngrok

app = Flask(__name__)


app.config['MYSQL_USER'] = 'sql12556114'
app.config['MYSQL_PASSWORD'] = 'gb22xs5mYh'
app.config['MYSQL_HOST'] = 'sql12.freemysqlhosting.net'
app.config['MYSQL_DB'] = 'sql12556114'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql=MySQL(app)

def get_df():
  cur = mysql.connection.cursor()
  cur.execute(query = "SELECT * FROM quiz")
  table_rows = cur.fetchall()
  df = pd.DataFrame(table_rows)
  cur.close()

  return df

# english_df = get_df()

# english_data = english_df[['Question_id','Question','Chapter','Difficulty']]
# english_data = english_data.dropna()
# english_data = english_data.astype({'Question_id': 'int'}) # with question id now for user item-item based recommendation
# # english_data['Difficulty']= english_data['Difficulty'].map(str)
# english_data = english_data.reset_index(drop=True)

# test_student = {"Question_ids": [10,20,30,40,50,60,70,80,90,99,25,75],
#               "Chapters": ["P1 Vocabulary", "P2 Plurals", "P2 Adjectives", "P3 Pronouns", "P3 Question wordings", "P4 Conjunction words", "P4 Conjunction words", "P5 Vocabulary", "P6 Pronouns", "P6 Pronouns", "P2 Plurals" ,"P5 Vocabulary"],
#               "Scores":[1,0,1,0,1,0,1,0,1,0,1,0]
#               }

def get_multi(q_list):
    cur = mysql.connection.cursor()
    cur.execute(query = "SELECT * FROM quiz where id IN %s" % str(tuple(int(i) for i in q_list)))
    results = cur.fetchall()
    # print(results)
    cur.close()
    return results

# #content-based focusing on the chapters of the individual questions for recommendations
# tf = TfidfVectorizer(analyzer='word',ngram_range=(1, 2),min_df=0, stop_words='english')
# tfidf_matrix = tf.fit_transform(english_data['Chapter'])
# cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix) # linear kernel is faster than the computation of cosine sim formula

# # Build a 1-dimensional array with movie titles
# questions = english_data['Question']
# indices = pd.Series(english_data.index, index=english_data['Question'])

# Function that get movie recommendations based on the cosine similarity score of movie genres
def questionRecommendations(question):
    english_df = get_df()

    english_data = english_df[['id','ques','chapter','difficulty']]
    english_data = english_data.dropna()
    english_data = english_data.astype({'id': 'int'}) # with question id now for user item-item based recommendation
    # english_data['Difficulty']= english_data['Difficulty'].map(str)
    english_data = english_data.reset_index(drop=True)

    #content-based focusing on the chapters of the individual questions for recommendations
    tf = TfidfVectorizer(analyzer='word',ngram_range=(1, 2),min_df=0, stop_words='english')
    tfidf_matrix = tf.fit_transform(english_data['chapter'])
    cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix) # linear kernel is faster than the computation of cosine sim formula

    # Build a 1-dimensional array with movie titles
    questions = english_data['ques']
    indices = pd.Series(english_data.index, index=english_data['ques'])

    quiz_questions = pd.DataFrame(columns=list(english_data.columns) + ['Prediction'])
    quiz_indicies = []

    idx = indices[question]
    sim_scores = list(enumerate(cosine_sim[idx])) # essentially the prediction for recommendation
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[0:30]
    question_indices = [i[0] for i in sim_scores]

    # print(question_indices)
    for count_i, question_i in enumerate(question_indices):
      # quiz_questions = pd.concat([quiz_questions, english_data.iloc[question_i]])
      new_row = list(english_data.values[question_i]) + [sim_scores[count_i][-1]]                                      # Create copy of DataFrame
      quiz_questions.loc[count_i] = new_row 

    # return questions.iloc[question_indices]# just question titles 
    return quiz_questions # pd dataframe is returned

@app.route("/", methods=["GET"])
def allos():
    return "ALLOS-QUIZ"


@app.route("/quiz")
def initial_quiz():
    ques_list = []
    n = 12
    for i in range(n):
        ques_list.append(random.randint(1, 99))

    return jsonify(get_multi(ques_list))


@app.route("/result",methods=["POST"])
def score():
    score = 0
    correct = []
    wrong = []
    ques = request.get_json()
    length = len(ques)
    ques = sorted(ques, key=lambda k: k["id"])
    ques_list = []
    scores = []
    chaps=[]
    for i in range(length):
        ques_list.append(ques[i]["id"])
    answers = jsonify(get_multi(ques_list))
    answers = answers.get_json()
    for i in range(length):
        chaps.append(answers[i]["chapter"])
        if ques[i]["ans"] == answers[i]["ans"]:
            score += 1
            scores.append(1)
            correct.append(int(ques[i]["id"]))
        else:
            scores.append(0)
            wrong.append(int(ques[i]["id"]))
    
    student_res = json.dumps({"Question_ids":ques_list,"Chapters":chaps,"Scores":scores})
    # print(student_res)
    recommendation = get_multi(generateRecommendationQuiz(student_res))
    result = jsonify({"Question_ids":ques_list,"Scores":scores,"score": score, "correct": correct, "wrong": wrong,"recommendation":recommendation})
    # result = jsonify(result)

    return result

# @app.route("/recommend")
def generateRecommendationQuiz(student_res):
  #dict of Question_ids, Chapters, Scores
  # studentResults = request.get_json()
  studentResults = json.loads(student_res)
  english_df = get_df()

  english_data = english_df[['id','ques','chapter','difficulty']]
  english_data = english_data.dropna()
  english_data = english_data.astype({'id': 'int'}) # with question id now for user item-item based recommendation
  # english_data['Difficulty']= english_data['Difficulty'].map(str)
  english_data = english_data.reset_index(drop=True)


  quiz_questions_final = pd.DataFrame(columns=list(english_data.columns) + ['Prediction'])
  recommended_question_idx = []
  
  question_idx = [] # for the dataframe's index
  correct_questions_idx_list = []
  wrong_questions_idx_list = []

  for i in range(len(studentResults["Question_ids"])):
    if (studentResults["Scores"][i] == 0): #If question is wrong
      wrong_questions_idx_list.append(studentResults["Question_ids"][i])
    else: #If question is right
      correct_questions_idx_list.append(studentResults["Question_ids"][i])

  #find the indices of all the question_id 
  for index, value in enumerate(wrong_questions_idx_list):
    row_index = english_data[english_data['id'] == value].index[0]
    question_idx.append(row_index)

  if len(question_idx) == 0: ## ~~ meaning all the questions this person has asked is correct ~~ ## Random unanswered questions will be asked 
    # print(" ----- You have answered all of the questions correctly... new questions will be asked... -----")
    quiz_questions_temp = english_data.copy()

    for index, value in enumerate(correct_questions_idx_list):
      drop_frame = quiz_questions_temp[quiz_questions_temp['id'] == value].index
      quiz_questions_final = quiz_questions_temp.drop(drop_frame, inplace=False)

    quiz_questions_final = quiz_questions_final.sample(n=36)
    quiz_questions_final = quiz_questions_final.sort_values(by=['Difficulty'], ascending = True)
    quiz_questions_final = quiz_questions_final.reset_index(drop=True, inplace=False) # can return the 36 question_idx in list

    display(quiz_questions_final)

    recommended_question_idx = list(quiz_questions_final['id'])
    recommended_question_idx = sample(recommended_question_idx, len(recommended_question_idx))

    return recommended_question_idx


  # print("----- You got some questions wrong... -----")
  # print("You got " + str(len(wrong_questions_idx_list))+ " questions wrong.")
  # print(wrong_questions_idx_list)

  for index, value in enumerate(question_idx):
    quiz_questions_temp = questionRecommendations(value) # returns with prediction also for sorting
    quiz_questions_final = pd.concat([quiz_questions_final, quiz_questions_temp])
  quiz_questions_final = quiz_questions_final.drop_duplicates(subset=['ques'])   #clear all dupes then sort by highest prediction

  for index, value in enumerate(correct_questions_idx_list): # remove correct questions from the recommendation
    drop_frame = quiz_questions_final[quiz_questions_final['id'] == value].index
    quiz_questions_final = quiz_questions_final.drop(drop_frame, inplace=False)

  quiz_questions_final = quiz_questions_final.sort_values(by=['Prediction'], ascending = False)
  quiz_questions_final = quiz_questions_final[0:36] # can sort with difficulty after this line
  quiz_questions_final = quiz_questions_final.reset_index(drop=True, inplace=False)

  # display(quiz_questions_final)

  recommended_question_idx = list(quiz_questions_final['id'])
  recommended_question_idx = sample(recommended_question_idx, len(recommended_question_idx))
  # recommended_question_idx = jsonify(recommended_question_idx)

  return recommended_question_idx


if(__name__) == "__main__":
    app.run()

